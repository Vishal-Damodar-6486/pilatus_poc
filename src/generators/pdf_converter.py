import markdown
from xhtml2pdf import pisa
from io import BytesIO

def convert_markdown_to_pdf(markdown_text):
    """
    Converts Markdown to PDF with fixed table layouts to prevent text overlap.
    """
    # 1. Convert Markdown to HTML
    html_body = markdown.markdown(markdown_text, extensions=['extra', 'tables'])
    
    # Path to logo
    import os
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../inputs/images/logo.png"))
    # Normalize path for Windows/xhtml2pdf
    logo_path = logo_path.replace("\\", "/")
    
    # 2. Add Native xhtml2pdf Styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2.0cm;
                margin-top: 3.5cm;
                margin-bottom: 3.5cm;
                
                @frame header_frame {{
                    -pdf-frame-content: header_content;
                    top: 1.5cm; margin-left: 2.0cm; margin-right: 2.0cm; height: 1.5cm;
                }}
                @frame footer_frame {{
                    -pdf-frame-content: footer_content;
                    bottom: 1.5cm; margin-left: 2.0cm; margin-right: 2.0cm; height: 1.0cm;
                }}
            }}
            
            body {{
                font-family: Helvetica, sans-serif;
                font-size: 10pt;
                line-height: 1.5; /* Improved readability */
                color: #333;
            }}

            /* HEADER & FOOTER */
            #header_content {{ 
                font-family: Helvetica, sans-serif; 
                font-size: 9pt; 
                color: #555; 
                border-bottom: 2px solid #002D62; /* Corporate Blue */
                height: 1.5cm;
            }}
            #footer_content {{ 
                font-family: Helvetica, sans-serif; 
                font-size: 8pt; 
                color: #777;
                text-align: center; 
                border-top: 1px solid #ccc;
                padding-top: 5px;
            }}
            
            /* HEADER TABLE for Logo alignment */
            table.header_table {{
                width: 100%;
                border: none;
                margin-bottom: 0px;
            }}
            table.header_table td {{
                border: none;
                padding: 0px;
                vertical-align: middle;
            }}

            /* HEADINGS */
            h1 {{ 
                font-size: 24pt; 
                color: #002D62; /* Corporate Blue */
                text-transform: uppercase; 
                border-bottom: 3px solid #002D62; 
                padding-bottom: 8px; 
                margin-top: 30px;
                margin-bottom: 20px;
                -pdf-outline: true; 
                -pdf-level: 0; 
                -pdf-open: false;
            }}
            h2 {{ 
                font-size: 16pt; 
                color: #002D62; /* Corporate Blue */
                margin-top: 25px; 
                margin-bottom: 15px;
                border-bottom: 1px solid #ccc; 
                padding-bottom: 5px;
                -pdf-outline: true; 
                -pdf-level: 1; 
                -pdf-open: false;
            }}
            h3 {{ 
                font-size: 12pt; 
                font-weight: bold; 
                color: #444;
                margin-top: 20px; 
                margin-bottom: 10px;
                -pdf-outline: true; 
                -pdf-level: 2; 
                -pdf-open: false;
            }}
            
            /* TABLES - THE FIX */
            table {{
                width: 100%;
                border: 0.5px solid #999;
                border-collapse: collapse;
                font-size: 9pt;
                margin-bottom: 20px;
            }}
            
            th {{
                background-color: #002D62; /* Corporate Blue Header */
                color: #ffffff;
                border: 0.5px solid #999;
                padding: 6px;
                font-weight: bold;
                text-align: left;
                vertical-align: middle;
            }}
            
            td {{
                border: 0.5px solid #999;
                padding: 6px;
                vertical-align: top;
                word-wrap: break-word; 
            }}
            
            /* Special styling for the wide Component Name column if possible */
            /* Note: xhtml2pdf doesn't support nth-child robustly, so we rely on general fit */

            blockquote {{
                background-color: #f9f9f9;
                border-left: 4px solid #002D62;
                padding: 10px;
                font-size: 9pt;
                margin: 15px 0;
            }}

            /* Image Centering */
            img {{
                display: block;
                margin-left: auto;
                margin-right: auto;
                text-align: center;
                max-width: 100%;
            }}

            /* TOC Styling */
            pdftoc {{
                color: #002D62;
            }}
            pdftoc.pdftoclevel0 {{
                font-weight: bold;
                margin-top: 10px;
                color: #002D62;
            }}
            pdftoc.pdftoclevel1 {{
                margin-left: 20px;
                color: #444;
            }}
            pdftoc.pdftoclevel2 {{
                margin-left: 40px;
                font-style: italic;
                color: #666;
            }}
            
            /* Specific Header for TOC to avoid Outline inclusion and page breaks */
            h1.toc-header {{
                font-size: 24pt;
                color: #002D62;
                text-transform: uppercase;
                border-bottom: 3px solid #002D62;
                padding-bottom: 8px;
                -pdf-outline: false;
                page-break-after: avoid; 
            }}
        </style>
    </head>
    <body>
        <div id="header_content">
            <table class="header_table">
                <tr>
                    <td style="text-align: left; width: 70%;">ER-24-AUTO-001 | Automated Stress Report | Issue 01</td>
                    <td style="text-align: right; width: 30%;">
                        <img src="{logo_path}" style="height: 45px;" />
                    </td>
                </tr>
            </table>
        </div>
        <div id="footer_content">
            Page <pdf:pagenumber> of <pdf:pagecount>
        </div>

        {html_body}
    </body>
    </html>
    """
    
    # 3. Inject TOC Placeholder *AFTER* HTML Generation
    # Markdown often wraps the placeholder in <p> tags, so we catch that too
    full_html = full_html.replace("<p>[[TOC_PLACEHOLDER]]</p>", "<pdf:toc />")
    full_html = full_html.replace("[[TOC_PLACEHOLDER]]", "<pdf:toc />")
    
    full_html = full_html.replace("<p>[[PDF_NEXTPAGE]]</p>", "<pdf:nextpage />")
    full_html = full_html.replace("[[PDF_NEXTPAGE]]", "<pdf:nextpage />")
    
    # 3. Render PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=pdf_buffer)
    
    if pisa_status.err:
        raise Exception(f"PDF Generation Error: {pisa_status.err}")
        
    return pdf_buffer