"""
Command-Line Interface for MorphSpot Digital Image Forensic Engine.

Usage:
    python cli.py --image path/to/image.jpg
    python cli.py --image path/to/image.jpg --output-dir ./results --save-masks
    python cli.py --dir path/to/images/ --output-dir ./batch_results
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.engine import ForensicEngine
from app.config import DEFAULT_CONFIG
from app.utils.image_io import load_image, array_to_pil
import cv2


# Ensure UTF-8 stdout encoding where possible
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def format_cli_output(report: dict):
    """Prints a structured summary table to terminal."""
    score = report["tampered_probability_percentage"]
    verdict = report["verdict"]
    confidence = report["confidence_level"]
    filename = report["filename"]

    print("\n" + "=" * 65)
    print(f" [*] MORPHSPOT FORENSIC REPORT: {filename}")
    print("=" * 65)
    print(f" Verdict                 : {verdict}")
    print(f" Tampered Probability    : {score:.1f}%")
    print(f" Confidence Level        : {confidence}")
    print("-" * 65)
    print(" FORENSIC BREAKDOWN:")

    bd = report["forensic_breakdown"]
    print(f"  [+] Error Level Analysis (ELA) : {bd['ela_analysis']['score_percentage']:>5.1f}% | {bd['ela_analysis']['details'][:40]}...")
    print(f"  [+] Noise Residual Consistency : {bd['noise_consistency']['score_percentage']:>5.1f}% | {bd['noise_consistency']['details'][:40]}...")
    print(f"  [+] Copy-Move / Clone Forgery  : {bd['copy_move_detection']['score_percentage']:>5.1f}% | {bd['copy_move_detection']['details'][:40]}...")
    print(f"  [+] Edge Gradient Sharpness    : {bd['edge_sharpness_inconsistency']['score_percentage']:>5.1f}% | {bd['edge_sharpness_inconsistency']['details'][:40]}...")
    meta_status = "[FLAGGED]" if bd['metadata_analysis']['flagged'] else "[CLEAN]"
    print(f"  [+] Metadata & EXIF Audit      : {meta_status} (Software: {bd['metadata_analysis']['software_detected']})")
    print("-" * 65)
    print(f" SUMMARY:\n {report['summary']}")
    print("=" * 65 + "\n")


def analyze_single_image(engine: ForensicEngine, image_path: str, output_dir: str = None, save_masks: bool = False):
    """Analyzes a single image file and optionally saves artifacts."""
    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}", file=sys.stderr)
        return False

    filename = os.path.basename(image_path)
    report = engine.analyze(source=image_path, filename=filename, include_all_visuals=save_masks)
    format_cli_output(report)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(image_path).stem
        json_path = os.path.join(output_dir, f"{base_name}_forensic_report.json")
        
        # Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f" [+] Report JSON saved to: {json_path}")

        if save_masks:
            img_rgb, _, _ = load_image(image_path)
            ela_res = engine.ela_detector.analyze(img_rgb)
            noise_res = engine.noise_detector.analyze(img_rgb)
            copy_res = engine.copy_move_detector.analyze(img_rgb)
            edge_res = engine.edge_detector.analyze(img_rgb)

            cv2.imwrite(os.path.join(output_dir, f"{base_name}_ela_heatmap.jpg"), cv2.cvtColor(ela_res["heatmap_rgb"], cv2.COLOR_RGB2BGR))
            cv2.imwrite(os.path.join(output_dir, f"{base_name}_noise_heatmap.jpg"), cv2.cvtColor(noise_res["heatmap_rgb"], cv2.COLOR_RGB2BGR))
            cv2.imwrite(os.path.join(output_dir, f"{base_name}_copymove_annotated.jpg"), cv2.cvtColor(copy_res["annotated_image"], cv2.COLOR_RGB2BGR))
            cv2.imwrite(os.path.join(output_dir, f"{base_name}_edge_heatmap.jpg"), cv2.cvtColor(edge_res["heatmap_rgb"], cv2.COLOR_RGB2BGR))
            print(f" [+] Visual heatmap masks saved to: {output_dir}")

    return True


def main():
    parser = argparse.ArgumentParser(description="MorphSpot: Digital Image Forensics & Tampering Detection CLI")
    parser.add_argument("--image", "-i", type=str, help="Path to single image file for analysis")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing images for batch analysis")
    parser.add_argument("--output-dir", "-o", type=str, help="Directory to save JSON reports and mask images")
    parser.add_argument("--save-masks", action="store_true", help="Save individual visual heatmap images")
    parser.add_argument("--json-only", action="store_true", help="Output raw JSON to stdout")

    args = parser.parse_args()

    if not args.image and not args.dir:
        parser.print_help()
        sys.exit(1)

    engine = ForensicEngine(DEFAULT_CONFIG)

    if args.image:
        if args.json_only:
            report = engine.analyze(source=args.image, filename=os.path.basename(args.image))
            print(json.dumps(report, indent=2))
        else:
            analyze_single_image(engine, args.image, args.output_dir, args.save_masks)

    elif args.dir:
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
        files = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if Path(f).suffix.lower() in valid_exts]
        print(f"Found {len(files)} images to analyze in {args.dir}...\n")
        for fpath in files:
            analyze_single_image(engine, fpath, args.output_dir, args.save_masks)


if __name__ == "__main__":
    main()
