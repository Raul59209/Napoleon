python -c "
import chardet, pathlib

path = 'dataset/correction_worksheet.tsv'
raw = pathlib.Path(path).read_bytes()
detected = chardet.detect(raw)
print('Detected encoding:', detected)

# Re-save as UTF-8
text = raw.decode(detected['encoding'])
pathlib.Path(path).write_text(text, encoding='utf-8')
print('Re-saved as UTF-8')
"