"""
Single-shot GeoChat inference — adapted from geochat/serve/cli.py.

Two real bugs fixed vs. the original file:
1. Original imports from a nonexistent `llava` module — everything actually
   lives under `geochat.*` in this repo (confirmed by inspecting the source).
2. Original has a leftover `import pdb; pdb.set_trace()` debug breakpoint
   that hangs any non-interactive run. Removed.

Also replaced the interactive input() loop with a single fixed question,
since we want one real answer, not a REPL, when calling this from a notebook.
"""
import argparse
import torch

from geochat.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN, DEFAULT_IM_START_TOKEN, DEFAULT_IM_END_TOKEN
from geochat.conversation import conv_templates, SeparatorStyle
from geochat.model.builder import load_pretrained_model
from geochat.utils import disable_torch_init
from geochat.mm_utils import process_images, tokenizer_image_token, get_model_name_from_path, KeywordsStoppingCriteria
from PIL import Image
from transformers import TextStreamer


def load_image(image_file):
    return Image.open(image_file).convert("RGB")


def main(args):
    disable_torch_init()

    model_name = get_model_name_from_path(args.model_path)
    print(f"[info] loading model from: {args.model_path}")
    print(f"[info] resolved model name: {model_name}")

    tokenizer, model, image_processor, context_len = load_pretrained_model(
        args.model_path, args.model_base, model_name, args.load_8bit, args.load_4bit, device=args.device
    )

    if "llama-2" in model_name.lower():
        conv_mode = "llava_llama_2"
    elif "v1" in model_name.lower():
        conv_mode = "llava_v1"
    elif "mpt" in model_name.lower():
        conv_mode = "mpt"
    else:
        conv_mode = "llava_v0"
    print(f"[info] using conversation template: {conv_mode}")

    conv = conv_templates[conv_mode].copy()
    roles = ("user", "assistant") if "mpt" in model_name.lower() else conv.roles

    image = load_image(args.image_file)
    image_tensor = process_images([image], image_processor, args)
    if isinstance(image_tensor, list):
        image_tensor = [img.to(model.device, dtype=torch.float16) for img in image_tensor]
    else:
        image_tensor = image_tensor.to(model.device, dtype=torch.float16)

    inp = args.question
    if model.config.mm_use_im_start_end:
        inp = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_TOKEN + DEFAULT_IM_END_TOKEN + "\n" + inp
    else:
        inp = DEFAULT_IMAGE_TOKEN + "\n" + inp

    conv.append_message(conv.roles[0], inp)
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()

    input_ids = tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt").unsqueeze(0).to(model.device)
    stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
    stopping_criteria = KeywordsStoppingCriteria([stop_str], tokenizer, input_ids)
    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    print(f"\n[question] {args.question}")
    print("[answer] ", end="", flush=True)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            images=image_tensor,
            do_sample=False,
            temperature=args.temperature,
            max_new_tokens=args.max_new_tokens,
            streamer=streamer,
            use_cache=True,
            stopping_criteria=[stopping_criteria],
        )

    outputs = tokenizer.decode(output_ids[0, input_ids.shape[1]:]).strip()
    print("\n\n[info] done.")
    print("[final_answer]", outputs)

    if args.output_json:
        import json
        with open(args.output_json, "w") as f:
            json.dump({"answer": outputs, "task": "vqa"}, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--image-file", type=str, required=True)
    parser.add_argument("--question", type=str, required=True)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--load-8bit", action="store_true")
    parser.add_argument("--load-4bit", action="store_true")
    parser.add_argument("--image-aspect-ratio", type=str, default="pad")
    parser.add_argument("--output-json", type=str, default=None,
                         help="If set, write {'answer':..., 'task':...} as JSON to this path — used by the FastAPI backend integration.")
    args = parser.parse_args()
    main(args)
