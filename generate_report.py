import re
import sys

def generate_markdown_report(log_path, output_path):
    with open(log_path, 'r') as log_file:
        log_content = log_file.read()

    architecture_match = re.search(r'\[INFO\] Architecture: (.+?)\.', log_path)
    architecture = architecture_match.group(1) if (architecture_match := re.search(r'\[INFO\] Architecture: (.+?)\.', log_content := open(log_path).read())) else 'Unknown'

    infinite_loops = re.findall(r'\[ALERT\] Potential infinite loops detected:\s*\n\s*Loop\s*\d+:\s*(0x[0-9A-Fa-f]+)', log_content)
    printable_strings = re.findall(r'0x[0-9A-Fa-f]+:\s*"([^"]{4,})"', log_content)

    with open(output_path, 'w') as report:
        report.write("# Firmware Analysis Report\n\n")
        report.write(f"## Architecture\n- {architecture}\n\n")

        report.write("## Infinite Loop Detection\n")
        if infinite_loops:
            report.write("⚠️ **Potential Infinite Loops Detected at addresses:**\n")
            for loop in infinite_loops:
                report.write(f"- `{loop}`\n")
        else:
            report.write("✅ **No Infinite Loops Detected**\n")

        printable_strings = re.findall(r'0x[0-9A-Fa-f]+:\s+\"(.+?)\"', log_content)
        report.write("\n## Printable Strings Extracted\n")
        if printable_strings:
            for s in printable_strings:
                report.write(f"- `{s}`\n")
        else:
            report.write("- No printable strings found.\n")

        report.write("\n## Recommendations\n")
        if infinite_loops:
            report.write("- ⚠️ **Review the code at the indicated loop addresses to resolve potential infinite loops.**\n")
        else:
            report.write("- ✅ **No immediate issues detected.**\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 generate_report.py <log_path> <output_path>")
        sys.exit(1)

    generate_markdown_report(sys.argv[1], sys.argv[2])