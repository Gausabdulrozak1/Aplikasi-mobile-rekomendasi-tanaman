from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


SRC = Path(r"D:\TaniAdaptif\outputs\manual-20260924-article\Artikel_Ilmiah_TaniAdaptif_Infotek.docx")
OUT = Path(r"D:\TaniAdaptif\outputs\manual-20260924-article\Artikel_Ilmiah_TaniAdaptif_Infotek_Revisi_Pendahuluan_Landasan.docx")


def clear_paragraph(paragraph):
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)


def set_text(paragraph, text, size=12, bold=False, italic=False, color=None):
    clear_paragraph(paragraph)
    run = paragraph.add_run(text)
    run.font.name = "Arial Narrow"
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Arial Narrow")
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Arial Narrow")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def insert_after(paragraph, text, style, size=12, bold=False):
    new_p = paragraph._parent.add_paragraph(style=style)
    set_text(new_p, text, size=size, bold=bold)
    paragraph._p.addnext(new_p._p)
    return Paragraph(new_p._p, paragraph._parent)


def remove_paragraph(paragraph):
    paragraph._p.getparent().remove(paragraph._p)


doc = Document(SRC)

# Revise only the four existing body paragraphs under Pendahuluan.
intro_heading = next(p for p in doc.paragraphs if p.text.strip() == "Pendahuluan")
intro_paragraphs = []
started = False
for p in doc.paragraphs:
    if p is intro_heading:
        started = True
        continue
    if started:
        if p.style.name.startswith("Heading"):
            break
        if p.text.strip():
            intro_paragraphs.append(p)

new_intro = [
    "Pertanian memiliki hubungan yang erat dengan cuaca dan iklim karena perubahan kondisi lingkungan dapat memengaruhi ketersediaan air, waktu tanam, dan pilihan komoditas. Dalam konteks tersebut, rotasi tanam menjadi salah satu pendekatan untuk menyusun urutan tanaman pada lahan yang sama secara lebih terarah. Penyesuaian pola tanam terhadap perubahan lingkungan merupakan bagian dari strategi adaptasi iklim, sedangkan diversifikasi melalui rotasi dapat mendukung ketahanan sistem pertanian [1], [17].",
    "Di Indonesia, informasi cuaca dapat diperoleh melalui layanan digital yang disediakan oleh Badan Meteorologi, Klimatologi, dan Geofisika (BMKG). Data terbuka BMKG dapat diakses dan diintegrasikan ke dalam aplikasi sehingga informasi cuaca tidak hanya ditampilkan, tetapi juga dapat diproses sebagai masukan sistem [18]. Pemanfaatan data tersebut membuka peluang untuk menghubungkan kondisi cuaca dengan informasi lahan ketika suatu rekomendasi tanaman akan disusun.",
    "Sejumlah penelitian telah memanfaatkan teknologi mobile, data lingkungan, dan sistem pendukung keputusan dalam bidang pertanian. Aplikasi Android dapat digunakan untuk menyajikan informasi cuaca bagi kegiatan pertanian [3], sedangkan sistem pendukung keputusan dapat membantu pemilihan tanaman berdasarkan sejumlah kriteria [4]. Namun, pendekatan-pendekatan tersebut belum memberikan alur yang sama dengan kebutuhan penelitian ini, yaitu menggabungkan data cuaca BMKG, kondisi lahan, tanaman sebelumnya, dan simulasi visual dalam satu aplikasi mobile.",
    "Simulasi visual dapat membantu menyajikan gambaran tanaman yang telah dipilih oleh sistem. Stable Diffusion merupakan model generatif text-to-image yang dapat menghasilkan gambar berdasarkan prompt, sedangkan fine-tuning dan Low-Rank Adaptation (LoRA) dapat digunakan untuk menyesuaikan karakter visual model terhadap dataset tertentu [5], [6]. Pada penelitian ini, Stable Diffusion 1.5 dengan LoRA ditempatkan setelah proses rekomendasi. Model generatif tidak menentukan tanaman, tetapi hanya menghasilkan visualisasi dari tanaman yang telah dipilih oleh rule-based engine.",
    "Berdasarkan celah tersebut, TaniAdaptif dikembangkan sebagai aplikasi mobile Android yang mengintegrasikan data cuaca BMKG, kondisi lahan, tanaman sebelumnya, dan rule-based engine berbasis decision table dengan Stable Diffusion 1.5 yang disesuaikan menggunakan LoRA. Seluruh komponen digunakan dalam satu alur simulasi rotasi tanam adaptif iklim di wilayah Aikmel dengan ruang lingkup padi, jagung, cabai, dan kacang tanah. Fokus penelitian berada pada perancangan, implementasi, dan pengujian teknis prototipe; penelitian ini tidak dimaksudkan sebagai validasi agronomi lapangan atau prediksi hasil panen.",
]
for old, text in zip(intro_paragraphs, new_intro):
    set_text(old, text)
if len(intro_paragraphs) > len(new_intro):
    for old in intro_paragraphs[len(new_intro):]:
        remove_paragraph(old)

# Replace only the previous Landasan Konsep body with five focused subparts.
paragraphs_snapshot = list(doc.paragraphs)
landasan_index = next(i for i, p in enumerate(paragraphs_snapshot) if p.text.strip() == "Landasan Konsep")
landasan_heading = paragraphs_snapshot[landasan_index]
following = paragraphs_snapshot[landasan_index + 1 :]
old_landasan_body = []
for p in following:
    if p.style.name.startswith("Heading 1"):
        break
    old_landasan_body.append(p)
for p in old_landasan_body:
    remove_paragraph(p)

concepts = [
    (
        "2.2.1 Rotasi Tanam dan Adaptasi Iklim",
        "Rotasi tanam adalah penyusunan tanaman secara bergantian pada lahan yang sama dalam periode tanam yang berbeda. Dalam penelitian ini, rotasi tanam dihubungkan dengan adaptasi iklim melalui penggunaan informasi cuaca, jenis lahan, ketersediaan air, dan tanaman sebelumnya. Konsep tersebut digunakan untuk membentuk rekomendasi tanaman berikutnya pada empat komoditas, bukan untuk memprediksi produktivitas atau hasil panen [1], [17].",
    ),
    (
        "2.2.2 Data Cuaca BMKG dan Sistem Rekomendasi",
        "Data BMKG berfungsi sebagai sumber informasi cuaca berdasarkan wilayah. Data yang diterima aplikasi dinormalisasi agar dapat digunakan bersama masukan kondisi lahan. Dengan cara ini, cuaca menjadi salah satu masukan dalam proses rekomendasi, sementara keputusan akhir tetap dibentuk oleh aturan sistem. Pemanfaatan data terbuka BMKG dalam aplikasi menjadi dasar integrasi informasi lingkungan pada penelitian ini [3], [18].",
    ),
    (
        "2.2.3 Rule-Based Engine dan Decision Table",
        "Rule-based engine merupakan pendekatan yang menghasilkan keluaran berdasarkan himpunan aturan yang telah ditentukan. Decision table digunakan untuk memetakan kombinasi kondisi masukan ke rekomendasi tertentu sehingga proses pengambilan keputusan dapat ditelusuri melalui kunci aturan dan rule ID. Pendekatan ini dipilih karena sesuai untuk rekomendasi dengan ruang lingkup terbatas dan membantu memisahkan fungsi keputusan dari model generatif [4], [12].",
    ),
    (
        "2.2.4 Stable Diffusion dan LoRA",
        "Stable Diffusion adalah model generatif text-to-image yang menghasilkan gambar dari prompt. Fine-tuning digunakan untuk menyesuaikan model yang telah tersedia terhadap karakteristik dataset, sedangkan LoRA menyediakan cara penyesuaian dengan parameter yang lebih ringan dibandingkan pelatihan ulang seluruh model [5], [6], [21], [22]. Dalam TaniAdaptif, Stable Diffusion 1.5 dan LoRA hanya digunakan untuk menghasilkan simulasi visual berdasarkan rekomendasi tanaman yang sudah ditentukan oleh rule-based engine.",
    ),
    (
        "2.2.5 Pengujian Sistem",
        "Black Box Testing memeriksa kesesuaian masukan, keluaran, dan status fungsi tanpa menilai struktur internal program. Pada penelitian ini, pendekatan tersebut digunakan bersama pengujian otomatis dan pemeriksaan artefak untuk memeriksa alur BMKG, decision table, layanan inference, penyimpanan, dan pengiriman gambar. Pengujian tersebut menjadi bukti fungsional dan teknis prototipe, bukan pengganti UAT atau validasi agronomi [25].",
    ),
]
cursor = landasan_heading
for heading, body in concepts:
    cursor = insert_after(cursor, heading, "Heading 3", size=11, bold=True)
    cursor = insert_after(cursor, body, "Body", size=12)

doc.core_properties.comments = "Revisi terbatas pada Pendahuluan dan Landasan Konsep; dokumen sumber skripsi tidak diubah."
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
