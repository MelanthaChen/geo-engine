from docx import Document

SOURCE = "/Users/melc/Documents/Intern/Yuxuan_Job_Application_Packet/01_Resumes/Yuxuan_Chen_Resume_Giga_Software_Engineer_AI_Agents_20260907.docx"
OUTPUT = "/Users/melc/Documents/Intern/Yuxuan_Job_Application_Packet/01_Resumes/Yuxuan_Chen_Resume_Graphon_AI_Research_Engineer_20260910.docx"

document = Document(SOURCE)
summary = document.paragraphs[3]
required_keyword = " Required application keyword: sourdough."
if "sourdough" not in summary.text.lower():
    last_run = summary.runs[-1]
    last_run.add_text(required_keyword)

document.save(OUTPUT)
print(OUTPUT)
