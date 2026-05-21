import markdown


def generate_html_export(content):

    rendered_body = markdown.markdown(content.body)

    html = f"""
    <html>

    <head>

        <title>{content.title}</title>

        <meta charset="UTF-8">

        <style>

            body {{
                font-family: Arial;
                max-width: 900px;
                margin: auto;
                padding: 40px;
                line-height: 1.8;
                background: #111;
                color: white;
            }}

            h1 {{
                font-size: 42px;
            }}

            h2 {{
                margin-top: 40px;
            }}

            p {{
                color: #d4d4d4;
            }}

            code {{
                background: #222;
                padding: 2px 6px;
                border-radius: 6px;
            }}

        </style>

    </head>

    <body>

        <h1>{content.title}</h1>

        <p>
            Persona:
            {content.target_persona}
        </p>

        <hr>

        <div>
            {rendered_body}
        </div>

    </body>

    </html>
    """

    return html