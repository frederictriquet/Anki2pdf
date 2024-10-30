import zstandard as zstd
import zipfile, sqlite3, os, re, sys, argparse
import tempfile
from xhtml2pdf import pisa

def convert_html_to_pdf(html_string, pdf_path):
  with open(pdf_path, "wb") as pdf_file:
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
  return not pisa_status.err

def unpack(input_path, output_path):
    dctx = zstd.ZstdDecompressor()
    with open(input_path, 'rb') as ifh, open(output_path, 'wb') as ofh:
        dctx.copy_stream(ifh, ofh)

def get_start(data):
    start1 = data.find(b'\x0A\x32')
    start2 = data.find(b'\x0A\x2D')
    if start1 == -1 and start2 == -1:
        start = -1
    elif start1 == -1 and start2 != -1:
        start = start2
    elif start1 != -1 and start2 == -1:
        start = start1
    else:
        start = min(start1, start2)
    return start

def enumerate_medias(input_path):
    with open(input_path, 'rb') as f:
        data = f.read()
        start = get_start(data)

        while start>=0:
            end = data.find(b'\x10', start)
            filename = str(data[start+2:end].decode())
            yield filename
            data = data[end+1:]
            start = get_start(data)


def dump_medias(input_path):
    for f in enumerate_medias(input_path):
        print(f)

def unpack_medias(directory_src, directory_dst, media_path):
    i = 0
    for i,f in enumerate(enumerate_medias(media_path)):
        unpack(f'{directory_src}/{i}',f'{directory_dst}/{f}')

def extract_all(archive_name, dest_dir_name, htmldir):
    with zipfile.ZipFile(f'{archive_name}', 'r') as zip_ref:
        zip_ref.extractall(f'{dest_dir_name}/')

    unpack(f'{dest_dir_name}/media', f'{dest_dir_name}/_media')
    unpack(f'{dest_dir_name}/collection.anki21b', f'{dest_dir_name}/_collection.anki21b')
    os.makedirs(htmldir, exist_ok=True)
    unpack_medias(f'{dest_dir_name}', htmldir, f'{dest_dir_name}/_media')

def db2html(db_filename, htmldir, title):
    connection = sqlite3.connect(db_filename)
    cursor = connection.cursor()
    cursor.execute("SELECT flds FROM notes")
    rows = cursor.fetchall()
    with open(f'{htmldir}/index.html', 'w') as html_file:
        html_file.write(f'<h1>{title}</h1>')
        for row in rows:
            content = row[0]
            # content = re.sub(r'\{\{c1::([^\}]*)\}\}', 'START<span style="color:blue">\\1</span>END', content, flags=re.MULTILINE)
            content = re.sub(r'\{\{c1::([^\}]*)\}\}', '<span style="color:blue">\\1</span>', content, flags=re.MULTILINE)
            content = re.sub(r'\{\{c2::([^\}]*)\}\}', '<span>\\1</span>', content, flags=re.MULTILINE)
            html_file.write(f'<hr>{content}')
            html_file.write(f'</span></span></span>')

def html2pdf(htmldir, pdf_filename):
    cwd = os.getcwd()
    os.chdir(htmldir)
    with open('index.html','r') as htmlfile:
        html = htmlfile.read()
        convert_html_to_pdf(html, pdf_filename)
        print(pdf_filename)
    os.chdir(cwd)

def process_all(apkg_filename:str, title:str):
    with tempfile.TemporaryDirectory() as tmpdirname:
        archive_name=apkg_filename
        htmldir=f'{tmpdirname}/HTML'
        # htmldir=f'./HTML'

        extract_all(archive_name, tmpdirname, htmldir)
        db2html(f'{tmpdirname}/_collection.anki21b', htmldir, title)

        pdf_filename = f'{os.getcwd()}/{title}.pdf'
        html2pdf(htmldir, pdf_filename)

def main():
    parser = argparse.ArgumentParser(
                    prog='anky2pdf',
                    description='Convertit un export Anki vers un fichier PDF',
                    epilog='.')
    parser.add_argument('title')
    parser.add_argument('filename')
    args = parser.parse_args()
    process_all(args.filename, args.title)
main()