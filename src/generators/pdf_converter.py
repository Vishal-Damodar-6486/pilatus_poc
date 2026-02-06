import markdown
from xhtml2pdf import pisa
from io import BytesIO

def convert_markdown_to_pdf(markdown_text):
    """
    Converts Markdown to PDF with fixed table layouts to prevent text overlap.
    """
    # 1. Convert Markdown to HTML
    html_body = markdown.markdown(markdown_text, extensions=['extra', 'tables'])
    
    # 2. Add Native xhtml2pdf Styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2.0cm; /* Slightly more space */
                margin-top: 3.5cm;
                margin-bottom: 3.5cm;
                
                @frame header_frame {{
                    -pdf-frame-content: header_content;
                    top: 1.5cm; margin-left: 2.0cm; margin-right: 2.0cm; height: 1.0cm;
                }}
                @frame footer_frame {{
                    -pdf-frame-content: footer_content;
                    bottom: 1.5cm; margin-left: 2.0cm; margin-right: 2.0cm; height: 1.0cm;
                }}
            }}
            
            body {{
                font-family: Helvetica, sans-serif;
                font-size: 10pt;
                line-height: 1.4;
            }}

            /* HEADER & FOOTER */
            #header_content {{ 
                font-family: Helvetica, sans-serif; 
                font-size: 9pt; 
                color: #666; 
                text-align: center; 
                border-bottom: 1px solid #ccc;
            }}
            #footer_content {{ 
                font-family: Helvetica, sans-serif; 
                font-size: 9pt; 
                text-align: center; 
                border-top: 1px solid #ccc;
                padding-top: 5px;
            }}

            /* HEADINGS */
            h1 {{ font-size: 18pt; text-transform: uppercase; border-bottom: 2px solid #000; padding-bottom: 5px; }}
            h2 {{ font-size: 14pt; margin-top: 25px; border-bottom: 1px solid #ccc; }}
            h3 {{ font-size: 12pt; font-weight: bold; margin-top: 15px; }}
            
            /* TABLES - THE FIX */
            table {{
                width: 100%;
                border: 0.5px solid #000;
                border-collapse: collapse;
                font-size: 9pt; /* Smaller font for tables */
                margin-bottom: 15px;
            }}
            
            th {{
                background-color: #f2f2f2;
                border: 0.5px solid #000;
                padding: 4px;
                font-weight: bold;
                text-align: left;
                vertical-align: top;
            }}
            
            td {{
                border: 0.5px solid #000;
                padding: 4px;
                vertical-align: top;
                /* Crucial for xhtml2pdf to handle wrapping */
                word-wrap: break-word; 
            }}
            
            /* Special styling for the wide Component Name column if possible */
            /* Note: xhtml2pdf doesn't support nth-child robustly, so we rely on general fit */

            blockquote {{
                background-color: #fafafa;
                border: 1px solid #ccc;
                padding: 10px;
                font-size: 9pt;
            }}
        </style>
    </head>
    <body>
        <div id="header_content">ER-24-AUTO-001 | Automated Stress Report | Issue 01</div>
        <div id="footer_content">
            Page <pdf:pagenumber> of <pdf:pagecount>
        </div>

        {html_body}
    </body>
    </html>
    """
    
    # 3. Render PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=pdf_buffer)
    
    if pisa_status.err:
        raise Exception(f"PDF Generation Error: {pisa_status.err}")
        
    pdf_buffer.seek(0)
    return pdf_buffer.read()