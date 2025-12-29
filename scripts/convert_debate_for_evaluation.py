"""Convert debate result to evaluator-compatible format."""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def convert_debate_to_transcript(debate_file: Path) -> str:
    """Convert debate JSON file to transcript format for evaluator.
    
    Args:
        debate_file: Path to debate JSON file
        
    Returns:
        Transcript text in evaluator-compatible format
    """
    try:
        with open(debate_file, 'r', encoding='utf-8') as f:
            debate_data = json.load(f)
    except Exception as e:
        print(f"Error reading debate file: {e}", file=sys.stderr)
        sys.exit(1)
    
    topic = debate_data.get("topic", "Unknown Topic")
    panel_responses = debate_data.get("panel_responses", [])
    
    # Group responses by round
    rounds: Dict[int, List[Dict[str, Any]]] = {}
    for response in panel_responses:
        round_num = response.get("round_number", 1)
        if round_num not in rounds:
            rounds[round_num] = []
        rounds[round_num].append(response)
    
    # Build transcript
    transcript_lines = [f"토론 주제: {topic}\n", "=" * 80, "\n"]
    
    for round_num in sorted(rounds.keys()):
        transcript_lines.append(f"\nRound {round_num}\n")
        transcript_lines.append("-" * 80)
        transcript_lines.append("\n")
        
        for response in rounds[round_num]:
            persona = response.get("persona", "Unknown")
            stance = response.get("stance", "")
            opinion = response.get("opinion", "")
            reasoning = response.get("reasoning", "")
            
            # Format: Persona (Stance): Opinion + Reasoning
            full_text = f"{opinion}\n\n{reasoning}" if reasoning else opinion
            
            transcript_lines.append(f"{persona} ({stance}):\n")
            transcript_lines.append(f"{full_text}\n\n")
    
    return "".join(transcript_lines)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python convert_debate_for_evaluation.py <debate_json_file> [output_file]")
        print("Example: python convert_debate_for_evaluation.py debates/debate_20241226_123456.json transcript.txt")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: File not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    
    # Convert to transcript
    transcript = convert_debate_to_transcript(input_file)
    
    # Output
    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(transcript, encoding='utf-8')
        print(f"Transcript saved to: {output_file}")
    else:
        print(transcript)


if __name__ == "__main__":
    main()

