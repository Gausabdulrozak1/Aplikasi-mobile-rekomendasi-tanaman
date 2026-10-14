from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


OUT = Path(r"D:\TaniAdaptif\outputs\manual-20260924-article\Artikel_Ilmiah_TaniAdaptif_Infotek.docx")


def set_run_font(run, name="Arial Narrow", size=None, bold=None, italic=None, color=None):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=60, start=80, bottom=60, end=80):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_geometry(table, widths_dxa):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:type"), "dxa")
    tbl_w.set(qn("w:w"), str(sum(widths_dxa)))
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:type"), "dxa")
    tbl_ind.set(qn("w:w"), "0")
    grid = tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths_dxa:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:type"), "dxa")
            tc_w.set(qn("w:w"), str(widths_dxa[i]))
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)


def set_table_borders(table, color="A6A6A6", size="4"):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_columns(section, count=2, space=360):
    sect_pr = section._sectPr
    cols = sect_pr.find(qn("w:cols"))
    if cols is None:
        cols = OxmlElement("w:cols")
        sect_pr.append(cols)
    cols.set(qn("w:num"), str(count))
    cols.set(qn("w:space"), str(space))
    cols.set(qn("w:equalWidth"), "1")


def set_keep_with_next(paragraph):
    p_pr = paragraph._p.get_or_add_pPr()
    keep = OxmlElement("w:keepNext")
    p_pr.append(keep)


def add_text(doc, text, style="Body", align=None, italic=False, color=None, bold=False):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_run_font(run, size=None, bold=bold, italic=italic, color=color)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    set_run_font(run, size={1: 12, 2: 12, 3: 11}[level], bold=True, color="000000")
    set_keep_with_next(p)
    return p


def add_placeholder(doc, label, description):
    p = doc.add_paragraph(style="Placeholder")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(f"[{label}]\n{description}")
    set_run_font(run, size=10, italic=True, color="666666")
    return p


def add_caption(doc, text):
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, size=9, bold=True)
    return p


def add_table(doc, headers, rows, widths, caption):
    add_caption(doc, caption)
    table = doc.add_table(rows=1, cols=len(headers))
    set_table_geometry(table, widths)
    set_table_borders(table)
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_shading(cell, "D9E2F3")
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(header)
        set_run_font(r, size=8.5, bold=True)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i != 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(str(value))
            set_run_font(r, size=8.3)
    set_table_geometry(table, widths)
    return table


def add_reference(doc, text):
    p = doc.add_paragraph(style="Reference")
    p.paragraph_format.first_line_indent = Cm(-0.35)
    p.paragraph_format.left_indent = Cm(0.35)
    r = p.add_run(text)
    set_run_font(r, size=9)
    return p


doc = Document()
section = doc.sections[0]
section.page_width = Cm(21.0)
section.page_height = Cm(29.7)
section.top_margin = Cm(2.5)
section.bottom_margin = Cm(2.5)
section.left_margin = Cm(2.5)
section.right_margin = Cm(2.5)
section.header_distance = Cm(1.0)
section.footer_distance = Cm(1.0)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Arial Narrow"
normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial Narrow")
normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial Narrow")
normal.font.size = Pt(12)
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_after = Pt(4)

for name, size, before, after in (("Body", 12, 0, 4), ("Abstract", 11, 0, 3), ("Heading 1", 12, 8, 4), ("Heading 2", 12, 6, 3), ("Heading 3", 11, 5, 2), ("Reference", 9, 0, 0), ("Caption", 9, 2, 2), ("Placeholder", 10, 3, 3)):
    if name in styles:
        style = styles[name]
    else:
        style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    style.font.name = "Arial Narrow"
    style._element.rPr.rFonts.set(qn("w:ascii"), "Arial Narrow")
    style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial Narrow")
    style.font.size = Pt(size)
    style.paragraph_format.space_before = Pt(before)
    style.paragraph_format.space_after = Pt(after)
    style.paragraph_format.line_spacing = 1.0 if name in {"Abstract", "Reference", "Caption", "Placeholder"} else 1.5

for level in (1, 2, 3):
    style = styles[f"Heading {level}"]
    style.font.bold = True
    style.font.color.rgb = RGBColor(0, 0, 0)
    style.paragraph_format.keep_with_next = True

# Header and footer follow the journal template without inventing a DOI.
header = section.header.paragraphs[0]
header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
header_run = header.add_run("INFOTEK: Jurnal Informatika dan Teknologi | e-ISSN 2614-8773")
set_run_font(header_run, size=8, color="666666")
footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer_run = footer.add_run("Naskah artikel ilmiah - TaniAdaptif")
set_run_font(footer_run, size=8, color="666666")

# Front matter: single column, as in the template.
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Rancang Bangun Aplikasi Mobile Berbasis Stable Diffusion dengan Fine-Tuning LoRA dan API BMKG untuk Simulasi Rotasi Tanam Adaptif Iklim di Wilayah Aikmel")
set_run_font(r, size=12, bold=True)
p.paragraph_format.space_after = Pt(8)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Gaus Abdul Rozak1*")
set_run_font(r, size=11, bold=True)
p.paragraph_format.space_after = Pt(2)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("1Program Studi Informatika, Fakultas Teknik, Universitas Hamzanwadi")
set_run_font(r, size=11)
p.paragraph_format.space_after = Pt(2)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("*Email penulis: [PERLU DIISI PENULIS]")
set_run_font(r, size=10, italic=True, color="666666")
p.paragraph_format.space_after = Pt(10)

add_heading(doc, "Abstrak", 1)
abstract = ("Sektor pertanian memiliki keterkaitan erat dengan kondisi cuaca sehingga penentuan pola tanam perlu mempertimbangkan informasi lingkungan secara terstruktur. Penelitian ini bertujuan merancang dan membangun aplikasi mobile TaniAdaptif untuk simulasi rotasi tanam adaptif iklim di wilayah Aikmel dengan mengintegrasikan data cuaca BMKG, kondisi lahan, rule-based engine, serta Stable Diffusion 1.5 dengan fine-tuning Low-Rank Adaptation (LoRA). Metode yang digunakan adalah Research and Development (R&D) yang meliputi identifikasi kebutuhan, pengumpulan data, perancangan, pengembangan, pengujian, dan penyempurnaan produk. Aplikasi dikembangkan menggunakan Flutter pada Android dengan backend Express, sedangkan rekomendasi tanaman ditentukan melalui decision table berdasarkan data cuaca, jenis lahan, ketersediaan air, dan tanaman sebelumnya. Dataset fine-tuning terdiri atas 389 gambar yang dibagi menjadi 312 data pelatihan dan 77 data validasi. Hasil pengujian menunjukkan seluruh 30 kombinasi aturan menghasilkan keluaran pada empat kelas komoditas. Evaluasi visual terhadap 36 pasangan gambar menunjukkan kesesuaian komoditas sebesar 86,11% pada model dasar dan 94,44% setelah menggunakan LoRA. Perbedaan tersebut belum signifikan berdasarkan Exact McNemar dengan p=0,25. Penelitian ini menghasilkan prototipe terintegrasi, dengan batasan bahwa keluaran tidak ditujukan sebagai validasi agronomi atau prediksi hasil panen.")
add_text(doc, abstract, style="Abstract")
add_text(doc, "Kata kunci: API BMKG, Fine-Tuning LoRA, Rotasi Tanam, Rule-Based Engine, Stable Diffusion", style="Abstract")

add_heading(doc, "Abstract", 1)
abstract_en = ("Agriculture is closely related to weather conditions; therefore, crop rotation planning needs to consider environmental information in a structured manner. This study aims to design and develop TaniAdaptif, a mobile application for climate-adaptive crop rotation simulation in the Aikmel area by integrating BMKG weather data, land conditions, a rule-based engine, and Stable Diffusion 1.5 with Low-Rank Adaptation (LoRA) fine-tuning. The Research and Development (R&D) method was applied through needs identification, data collection, design, development, testing, and product refinement. The application was developed using Flutter for Android with an Express backend, while crop recommendations were determined through a decision table based on weather data, land type, water availability, and the previous crop. The fine-tuning dataset consisted of 389 images, divided into 312 training images and 77 validation images. Testing showed that all 30 rule combinations produced outputs within the four predefined commodity classes. Visual evaluation of 36 image pairs showed commodity correctness of 86.11% for the base model and 94.44% after applying LoRA. The difference was not statistically significant based on the exact McNemar test (p=0.25). The study produced an integrated prototype, with the limitation that its outputs are not intended for agronomic validation or crop-yield prediction.")
add_text(doc, abstract_en, style="Abstract")
add_text(doc, "Keywords: BMKG API, Crop Rotation, Fine-Tuning LoRA, Rule-Based Engine, Stable Diffusion", style="Abstract")

# Begin two-column body.
body_section = doc.add_section(WD_SECTION.CONTINUOUS)
body_section.page_width = Cm(21.0)
body_section.page_height = Cm(29.7)
body_section.top_margin = Cm(2.5)
body_section.bottom_margin = Cm(2.5)
body_section.left_margin = Cm(2.5)
body_section.right_margin = Cm(2.5)
body_section.header_distance = Cm(1.0)
body_section.footer_distance = Cm(1.0)
set_columns(body_section, 2, 360)

add_heading(doc, "Pendahuluan", 1)
add_text(doc, "Sektor pertanian memiliki keterkaitan erat dengan cuaca dan iklim karena perubahan kondisi atmosfer dapat memengaruhi ketersediaan air, waktu tanam, serta pilihan tanaman. Penyesuaian pola tanam terhadap kondisi lingkungan merupakan salah satu bentuk adaptasi yang dapat digunakan dalam kegiatan pertanian [1]. Informasi curah hujan juga dapat menjadi bahan pertimbangan dalam menentukan waktu tanam [2]. Namun, data cuaca belum secara langsung menghasilkan rekomendasi rotasi tanaman karena perlu dipadukan dengan jenis lahan, ketersediaan air, dan tanaman sebelumnya.")
add_text(doc, "BMKG menyediakan informasi cuaca berdasarkan wilayah yang dapat diakses dan diintegrasikan ke dalam aplikasi. Pemanfaatan data tersebut memungkinkan informasi cuaca diproses sebagai masukan, bukan hanya ditampilkan. Penelitian tentang aplikasi Android untuk pemantauan cuaca pertanian menunjukkan bahwa perangkat mobile dapat menjadi media penyajian informasi lingkungan [3]. Pada sisi pengambilan keputusan, sistem pendukung keputusan pertanian telah digunakan untuk kesesuaian lahan dan pemilihan tanaman [4]. Penelitian ini mengambil posisi berbeda dengan menggabungkan API BMKG, aplikasi mobile, rule-based engine, dan simulasi visual generatif dalam satu prototipe.")
add_text(doc, "Stable Diffusion dapat menghasilkan gambar berdasarkan prompt dan dapat disesuaikan melalui fine-tuning [5]. LoRA digunakan sebagai teknik penyesuaian yang melatih parameter berukuran lebih kecil tanpa melatih ulang seluruh bobot model [6]. Dalam penelitian ini, Stable Diffusion dan LoRA tidak berperan sebagai pengambil keputusan. Rule-based engine menentukan komoditas yang direkomendasikan, sedangkan model generatif hanya menghasilkan simulasi visual setelah rekomendasi tersedia.")
add_text(doc, "Wilayah Aikmel digunakan sebagai konteks penerapan sistem. Aplikasi yang dibangun memproses cuaca BMKG dan input kondisi lahan untuk menghasilkan rekomendasi pada empat komoditas, yaitu padi, jagung, cabai, dan kacang tanah. Rumusan masalah penelitian mencakup perancangan aplikasi mobile terintegrasi, penerapan fine-tuning LoRA untuk simulasi visual, serta pengujian fungsional dan evaluasi teknis model. Penelitian dibatasi pada prototipe perangkat lunak; penelitian tidak mengukur produktivitas, tidak melakukan prediksi hasil panen, tidak melakukan validasi agronomi mendalam, dan tidak melakukan UAT atau survei penerimaan pengguna.")

add_heading(doc, "Tinjauan Pustaka", 1)
add_heading(doc, "Penelitian Terkait", 2)
add_text(doc, "Penelitian terkait menunjukkan beberapa pendekatan teknologi informasi dalam bidang pertanian. Suhartini dkk. mengembangkan sistem informasi geografis untuk pemetaan lahan pertanian di Lombok Timur [7], sedangkan Amri Muliawan Nur dkk. memetakan lokasi penjualan sarana pertanian berbasis GIS [8]. Fajar dan Waluyo mengembangkan sistem monitoring dan penyiraman bibit sawit berbasis Android dengan sensor lingkungan [9]. Gunawan dkk. menggunakan IoT untuk monitoring kualitas tanah tanaman herbal [10], sementara penelitian lain mengembangkan dashboard monitoring NPK dan pH tanah berbasis AI dan IoT [11].")
add_text(doc, "Naisali dkk. menggunakan Fuzzy Weighted Product untuk pemilihan tanaman pangan [12]. Muzakki dkk. membahas aplikasi Smart Farm berbasis Android dengan metode Waterfall [13]. Pemanfaatan informasi BMKG juga dibahas oleh Hartanto dkk. [14], sedangkan sistem rekomendasi berbasis Android dan aplikasi bercocok tanam menjadi rujukan tambahan [15], [16]. Penelitian TaniAdaptif melengkapi arah tersebut melalui integrasi data BMKG, input kondisi lahan, aturan deterministik, dan simulasi visual Stable Diffusion-LoRA.")
add_heading(doc, "Landasan Konsep", 2)
add_text(doc, "Rotasi tanam dalam penelitian ini dimaknai sebagai penyusunan rekomendasi tanaman berikutnya dengan mempertimbangkan kondisi cuaca, jenis lahan, ketersediaan air, dan tanaman sebelumnya. Kaitannya dengan adaptasi iklim berada pada penggunaan informasi lingkungan untuk membantu menyusun simulasi pola tanam, bukan untuk memprediksi hasil panen. Diversifikasi melalui rotasi dapat berkontribusi terhadap ketahanan sistem pertanian [17].")
add_text(doc, "API BMKG berfungsi sebagai sumber data cuaca. Data terbuka BMKG dapat diakses dan dimanfaatkan melalui mekanisme pertukaran data [18]. Data tersebut dinormalisasi sebelum digunakan pada proses rekomendasi. Rule-based engine dibangun dalam bentuk decision table agar setiap keluaran dapat ditelusuri melalui kunci dan rule ID. Pendekatan ini berbeda dari AHP, SAW, atau Fuzzy Weighted Product karena penelitian menggunakan aturan deterministik terbatas pada empat kelas komoditas [4], [12].")
add_text(doc, "Flutter digunakan untuk membangun aplikasi Android dengan satu basis kode [19]. Komunikasi antara aplikasi dan backend menggunakan API/REST API [20]. Stable Diffusion dipahami sebagai model generatif berbasis latent diffusion [21], sedangkan LoRA digunakan untuk menyesuaikan model dengan dataset visual yang spesifik [6], [22]. Perancangan perangkat lunak didokumentasikan menggunakan UML [23], dan struktur data dijelaskan melalui ERD [24]. Pengujian fungsional menggunakan pendekatan Black Box Testing [25].")

add_heading(doc, "Metode Penelitian", 1)
add_heading(doc, "Desain Penelitian dan Tahapan", 2)
add_text(doc, "Penelitian menggunakan metode Research and Development (R&D) karena menghasilkan artefak perangkat lunak berupa aplikasi mobile beserta komponen pendukungnya. R&D dilakukan melalui identifikasi kebutuhan, pengumpulan data, perancangan produk, pengembangan produk, pengujian produk, dan penyempurnaan produk. Pemilihan R&D sesuai dengan penelitian yang berorientasi pada pengembangan dan evaluasi produk [26], [27].")
add_placeholder(doc, "GAMBAR 1 - ALUR PENELITIAN", "Masukkan gambar alur R&D dari skripsi pada bagian ini; jangan membuat gambar baru.")
add_caption(doc, "Gambar 1. Alur penelitian")
add_heading(doc, "Objek, Lokasi, dan Data", 2)
add_text(doc, "Objek penelitian adalah kebutuhan informasi pertanian di wilayah Kecamatan Aikmel, Kabupaten Lombok Timur, Nusa Tenggara Barat. Variabel masukan terdiri atas kategori cuaca, jenis lahan, ketersediaan air, dan tanaman sebelumnya. Data cuaca diperoleh dari API BMKG. Data visual digunakan untuk fine-tuning dan dibatasi pada padi, jagung, cabai, dan kacang tanah. Penelitian tidak menggunakan data hasil panen, data laboratorium tanah, atau validasi ahli agronomi.")
add_table(doc, ["Komoditas", "Total", "Train", "Validation"], [["Padi", 95, 76, 19], ["Jagung", 100, 80, 20], ["Cabai", 97, 78, 19], ["Kacang tanah", 97, 78, 19], ["Total", 389, 312, 77]], [1300, 900, 1000, 1300], "Tabel 1. Distribusi dataset final")
add_heading(doc, "Arsitektur Sistem", 2)
add_text(doc, "Arsitektur sistem memisahkan fungsi keputusan dan fungsi visual. Aplikasi Flutter meminta data cuaca dan mengirim kondisi lahan melalui backend Express. Backend mengambil serta menormalisasi data BMKG, kemudian rule-based engine membentuk rekomendasi. Jika pengguna meminta visualisasi, konteks rekomendasi diteruskan melalui proxy Express ke layanan FastAPI pada lingkungan GPU. FastAPI menjalankan Stable Diffusion 1.5 dengan bobot LoRA, lalu gambar dikirim kembali melalui Express ke aplikasi Android.")
add_placeholder(doc, "GAMBAR 2 - ARSITEKTUR SISTEM", "Masukkan diagram arsitektur aplikasi dari skripsi: Flutter -> Express -> BMKG/Rule Engine dan Express -> FastAPI GPU -> Stable Diffusion + LoRA.")
add_caption(doc, "Gambar 2. Arsitektur sistem TaniAdaptif")
add_heading(doc, "Konfigurasi Fine-Tuning dan Evaluasi", 2)
add_table(doc, ["Parameter", "Nilai", "Parameter", "Nilai"], [["Model dasar", "Stable Diffusion 1.5", "Resolusi", "512 x 512"], ["LoRA rank", "8", "Batch size", "1"], ["Gradient accumulation", "4", "Learning rate", "0,0001"], ["Main training", "1.600 langkah", "Smoke test", "100 langkah"], ["Mixed precision", "FP16", "Optimizer", "8-bit Adam"], ["Seed", "42", "GPU", "NVIDIA Tesla T4"]], [1250, 1050, 1450, 1050], "Tabel 2. Konfigurasi fine-tuning dan lingkungan komputasi")
add_text(doc, "Evaluasi visual dilakukan dengan membandingkan Stable Diffusion dasar dan Stable Diffusion dengan LoRA menggunakan kondisi eksperimen yang disetarakan, termasuk prompt, seed, jumlah langkah inference, dan konfigurasi pembangkitan. Evaluasi menggunakan 36 pasangan gambar, dengan sembilan kondisi untuk setiap komoditas. Penilaian dilakukan terhadap kesesuaian komoditas, konteks, dan realisme sesuai prosedur yang dicatat dalam skripsi. Hasilnya dibaca sebagai evaluasi teknis pada ruang lingkup dataset dan kondisi eksperimen, bukan sebagai validasi agronomi.")

add_heading(doc, "Hasil dan Pembahasan", 1)
add_heading(doc, "Implementasi Sistem", 2)
add_text(doc, "Aplikasi mobile TaniAdaptif diimplementasikan pada platform Android menggunakan Flutter. Fungsi utama meliputi dashboard cuaca, input kondisi lahan, tampilan rekomendasi, kalender empat minggu, permintaan simulasi visual, cache, dan riwayat visual. Backend Express menjadi perantara antara aplikasi, BMKG, dan layanan inference. Pemisahan ini menjaga token inference dan URL upstream tidak disimpan langsung pada aplikasi mobile.")
add_placeholder(doc, "GAMBAR 3 - TAMPILAN APLIKASI", "Masukkan screenshot dashboard, form kondisi lahan, hasil rekomendasi, atau riwayat dari aplikasi yang sudah tersedia.")
add_caption(doc, "Gambar 3. Tampilan aplikasi mobile TaniAdaptif")
add_heading(doc, "Integrasi BMKG dan Kalender Rekomendasi", 2)
add_text(doc, "Respons BMKG wilayah Aikmel dengan kode ADM4 52.03.09.2002 berhasil diproses. Catatan pengujian mencatat 18 titik prakiraan untuk horizon tiga hari dan 18 titik curah hujan tersedia dari 18 titik. Parser mempertahankan nilai curah hujan sebagai null apabila field tidak tersedia, sehingga sistem tidak membuat nilai fiktif. Cache cuaca memiliki urutan fallback network, fresh-cache, dan stale-cache ketika terjadi gangguan jaringan.")
add_text(doc, "Karena horizon BMKG yang digunakan bersifat pendek, kalender empat minggu pada aplikasi bukan prakiraan iklim bulanan resmi. Minggu pertama menggunakan ringkasan harian yang tersedia, sedangkan minggu kedua sampai keempat menggunakan proyeksi rata-rata dengan tingkat keyakinan rendah. Keterangan ini ditampilkan agar kalender dipahami sebagai simulasi aktivitas berdasarkan kondisi saat permintaan.")
add_heading(doc, "Rule-Based Engine", 2)
add_text(doc, "Rule-based engine menggunakan 30 kunci utama yang dibentuk dari tiga kategori curah hujan, dua kategori ketersediaan air untuk pencarian aturan, dan lima nilai tanaman sebelumnya. Jenis lahan digunakan untuk penyesuaian prioritas, sedangkan empat kelas keluaran dibatasi pada padi, jagung, cabai, dan kacang tanah. Setiap hasil membawa daftar prioritas, alasan, ringkasan input, kunci aturan, dan rule ID. Seluruh 30 kunci menghasilkan keluaran dalam empat kelas yang ditetapkan.")
add_text(doc, "Hasil tersebut menunjukkan terpenuhinya kontrak perangkat lunak pada decision table. Hasil ini tidak dapat ditafsirkan sebagai bukti kebenaran agronomi universal karena aturan tidak memakai hasil laboratorium tanah, varietas, hama, harga pasar, atau prediksi hasil panen.")
add_heading(doc, "Fine-Tuning LoRA dan Simulasi Visual", 2)
add_text(doc, "Dataset final berjumlah 389 gambar, terdiri atas 312 gambar pelatihan dan 77 gambar validasi. Training akhir menggunakan Stable Diffusion 1.5 dengan LoRA rank 8 dan berlangsung selama 1.600 langkah pada lingkungan GPU NVIDIA Tesla T4. Bobot LoRA final dicatat sebagai multisource_multicrop_lora.safetensors dengan ukuran 6.414.992 byte, 256 tensor, dan SHA-256 0bda8908d577513110c22cf5ec1b8a7e008d2b26dd90525732a5c4e4b1bdd43a.")
add_text(doc, "Pada tahap inference, rekomendasi tanaman tetap ditentukan oleh rule-based engine. Stable Diffusion dan LoRA hanya menghasilkan gambar berdasarkan prompt dan konteks rekomendasi. Layanan FastAPI menyediakan pemeriksaan health, readiness, model info, validasi input, timeout, retry terbatas, validasi hash LoRA, serta pemeriksaan CUDA. Kegagalan layanan visual dipisahkan dari hasil rekomendasi sehingga rekomendasi tetap dapat ditampilkan ketika GPU atau provider visual tidak tersedia.")
add_placeholder(doc, "GAMBAR 4 - HASIL SIMULASI VISUAL", "Masukkan screenshot hasil simulasi visual dari aplikasi untuk empat komoditas jika akan digunakan dalam naskah.")
add_caption(doc, "Gambar 4. Hasil simulasi visual")
add_heading(doc, "Evaluasi Visual Base dan LoRA", 2)
add_table(doc, ["Indikator", "Base", "LoRA", "Keterangan"], [["Pasangan gambar", "36", "36", "Kondisi eksperimen berpasangan"], ["Kesesuaian komoditas", "86,11%", "94,44%", "Selisih deskriptif 8,33 poin persentase"], ["Exact McNemar", "-", "p=0,25", "Belum signifikan pada taraf 0,05"], ["Median konteks/realisme", "4,5", "4,0", "Ringkasan penilaian visual"], ["Exact sign test", "-", "p=0,6072387695", "Uji eksploratif sesuai skripsi"]], [1250, 850, 850, 1550], "Tabel 3. Hasil evaluasi visual Base dan LoRA")
add_text(doc, "Kesesuaian komoditas meningkat secara deskriptif dari 86,11% menjadi 94,44%, dengan selisih 8,33 poin persentase. Namun, Exact McNemar menghasilkan p=0,25 sehingga perbedaan belum signifikan pada taraf 0,05. Median konteks dan realisme keseluruhan turun dari 4,5 pada Base menjadi 4,0 pada LoRA, dengan exact sign test p=0,6072387695. Dengan demikian, LoRA membantu penyesuaian identitas visual dalam beberapa kondisi, tetapi belum membuktikan peningkatan seragam pada semua dimensi kualitas gambar.")
add_heading(doc, "Pengujian Fungsional dan Integrasi", 2)
add_table(doc, ["Komponen", "Cakupan atau hasil", "Status"], [["Python", "125 test otomatis", "Lulus menurut skripsi"], ["Backend", "23 test; BMKG, rule, proxy, error", "Lulus"], ["Flutter", "13 test; cache, storage, widget", "Lulus"], ["UI review", "18 review teknis", "Lulus"], ["Decision table", "30/30 kunci menghasilkan keluaran valid", "Lulus"], ["Human review", "72 penilaian pada 36 pasangan", "Lulus"], ["E2E GPU dan Android", "Jalur Flutter-backend-FastAPI-CUDA-LoRA-PNG", "Dicatat sudah diuji"]], [1100, 2450, 950], "Tabel 4. Ringkasan pengujian yang dilaporkan dalam skripsi")
add_text(doc, "Pengujian menggunakan Black Box Testing berbasis kontrak, unit/integration test otomatis, pemeriksaan artefak, dan respons live yang terdokumentasi. Bukti teknis mencakup parser BMKG, cache, decision table, validasi inference, retry, proxy, storage, widget Flutter, hash model, struktur SafeTensors, manifest, dan keterbacaan PNG. Pengujian ini bukan UAT. Penelitian tidak melaporkan responden petani, wawancara, kuesioner pengguna, atau validasi ahli agronomi.")
add_heading(doc, "Keterbatasan", 2)
add_text(doc, "Pertama, horizon prakiraan BMKG yang pendek membuat kalender empat minggu bersifat proyeksi aplikasi, bukan prakiraan bulanan resmi. Kedua, rule-based engine hanya mencakup empat komoditas dan variabel yang dibatasi, sehingga tidak dimaksudkan untuk memprediksi hasil panen atau menggantikan pertimbangan agronomi. Ketiga, dataset berjumlah 389 gambar dan sumber lokal Aikmel hanya tersedia pada sebagian kelas padi, sedangkan kelas lainnya berasal dari sumber publik. Keempat, evaluasi visual dilakukan oleh peneliti pada 36 pasangan tanpa verifikasi independen terhadap identitas penilai. Kelima, metrik teknis tidak mengukur penerimaan pengguna atau dampak praktik pertanian nyata.")

add_heading(doc, "Kesimpulan", 1)
add_text(doc, "Penelitian ini menghasilkan prototipe aplikasi mobile TaniAdaptif untuk simulasi rotasi tanam adaptif iklim di wilayah Aikmel. Aplikasi Flutter terhubung dengan backend Express untuk memproses data BMKG, menerima kondisi lahan, dan menghasilkan rekomendasi melalui rule-based engine berbasis decision table. Pengujian terhadap 30 kunci menunjukkan keluaran berada pada empat kelas komoditas yang telah ditetapkan.")
add_text(doc, "Fine-tuning LoRA pada Stable Diffusion 1.5 diterapkan sebagai modul pembangkit simulasi visual setelah rekomendasi ditentukan. Dataset terdiri atas 389 gambar dengan pembagian 312 data pelatihan dan 77 data validasi, sedangkan training akhir berlangsung selama 1.600 langkah. Evaluasi terhadap 36 pasangan menunjukkan kesesuaian komoditas 86,11% pada Base dan 94,44% pada LoRA. Selisih deskriptif 8,33 poin persentase belum signifikan berdasarkan Exact McNemar dengan p=0,25.")
add_text(doc, "Secara teknis, fungsi utama aplikasi dan integrasi komponen dilaporkan dapat berjalan sesuai rancangan, termasuk jalur BMKG, rekomendasi, penyimpanan, layanan inference, pengiriman PNG, lingkungan GPU, dan perangkat Android. Kesimpulan ini terbatas pada pengujian perangkat lunak dan evaluasi teknis yang tersedia. Penelitian tidak melakukan UAT, validasi agronomi lapangan, atau pengukuran efektivitas aplikasi bagi petani.")

add_heading(doc, "Daftar Pustaka", 1)
references = [
    '[1] R. H. M. W. Priyanto and H. Toiba, "Strategi Adaptasi Perubahan Iklim: Faktor Yang Mempengaruhi dan Manfaat Penerapannya," vol. 5, pp. 1169-1178, 2021, doi: 10.21776/ub.jepa.2021.005.04.19.',
    '[2] S. Defiyanti, B. N. Sari, and T. N. Padilah, "Optimasi Pertanian Padi: Peramalan Curah Hujan Berbasis Arima Untuk Penentuan Waktu Tanam Yang Tepat," J. Teknol. Inf. dan Ilmu Komput., vol. 11, no. 6, pp. 1377-1384, 2024, doi: 10.25126/jtiik.2024118682.',
    '[3] M. I. M. Idris, M. S. Said, and B. Rahman, "Sistem Informasi Pemantauan Data Cuaca Berbasis Android Untuk Mendukung Pertanian Di Kabupaten Konawe Selatan," Simtek J. Sist. Inf. dan Tek. Komput., vol. 10, no. 2, pp. 528-533, 2025, doi: 10.51876/simtek.v10i2.1682.',
    '[4] S. R. Wulandari, H. Hamdani, and A. Septiarini, "Sistem Pendukung Keputusan Kesesuaian Lahan Tanaman Padi Menggunakan Metode AHP dan SAW," JISKA, vol. 7, no. 3, pp. 226-236, 2022, doi: 10.14421/jiska.2022.7.3.226-236.',
    '[5] N. L. W. S. R. Ginantra, T. Hendrawati, and D. A. P. Wulandari, "Penerapan Metode Stable Diffusion Dengan Fine Tuning Untuk Pola Endek Bali," Tematik, vol. 11, no. 2, pp. 141-147, 2024, doi: 10.38204/tematik.v11i2.2069.',
    '[6] N. Mukaromah, S. Mulyono, U. Islam, and S. Agung, "Implementasi Stable Diffusion Dan Fine-Tuning Low Rank Adaptation Untuk Pembuatan Logo," J. Rekayasa Sist. Inf. dan Teknol., vol. 2, no. 3, pp. 973-984, 2025, doi: 10.70248/jrsit.v2i3.1885.',
    '[7] L. K. Wijaya, S. Putra, H. M. Mandala, and M. Saiful, "Sistem Informasi Berbasis Web Untuk Pemetaan Geografis Lahan Pertanian," J. Inform. dan Teknol., vol. 6, no. 1, pp. 127-137, 2023, doi: 10.29408/jit.v6i1.7521.',
    '[8] A. M. Nur, A. Sudianto, and Salmiah, "Pemetaan Lokasi Penjualan Pupuk Dan Obat-Obatan Pertanian Di Kabupaten Sumbawa Berbasis GIS," vol. 5, no. 2, 2022, doi: 10.29408/jit.v5i2.5891.',
    '[9] M. H. Fajar and A. F. Waluyo, "Sistem Monitoring dan Penyiraman Otomatis Pada Bibit Sawit Berbasis Android," Infotek J. Inform. dan Teknol., vol. 7, no. 1, pp. 123-132, 2024, doi: 10.29408/jit.v7i1.24026.',
    '[10] I. Gunawan, M. Sadali, and L. K. Wijaya, "Implementasi Internet Of Things (IOT) Untuk Monitoring Kualitas Tanah Tanaman Herbal Dengan Integrasi QR Code," vol. 2, no. 2, pp. 306-312, 2024, doi: 10.29408/jit.v8i2.31101.',
    '[11] I. Gunawan, M. N. Wathani, and Zulkipli, "Pengembangan Web Dashboard Monitoring Kadar Nitrogen, Fosfat, Kalium (NPK), PH Tanah Berbasis Artificial Intelligence dan Internet Of Things," vol. 9, no. 2, pp. 491-501, 2026, doi: 10.29408/jit.v9i2.34982.',
    '[12] A. Naisali, Y. P. K. Kelen, R. Syarifuddin, and D. G. Ludji, "Sistem Pendukung Keputusan Pemilihan Tanaman Pangan Berbasis Web dengan Fuzzy Weighted Product," J. Simantec, vol. 14, no. 1, pp. 21-36, 2025, doi: 10.21107/simantec.v14i1.29958.',
    '[13] A. Muzakki, A. M. A. Amri, M. I. Alhari, and F. Sadam, "Implementasi Aplikasi Smart Farm Berbasis Android Menggunakan Metode Waterfall," J. Algoritm., vol. 22, no. 1, pp. 801-807, 2025, doi: 10.33364/algoritma/v.22-1.2286.',
    '[14] B. Hartanto, N. Astriawati, Supartini, and D. K. Yekti, "Pencarian dan Pemanfaatan Informasi Data Badan Meteorologi, Klimatologi, dan Geofisika (BMKG)," INSOLOGI J. Sains dan Teknol., vol. 1, no. 5, pp. 553-564, 2022, doi: 10.55123/insologi.v1i5.906.',
    '[15] D. S. Sani and F. Nurpandi, "REKOMPOS: Android-Based Recommendation System for Edible," vol. 15, no. 1, 2025, doi: 10.35194/agsci.v15i1.5258.',
    '[16] N. A. Pratama, D. Afriyantari, and P. Putri, "Perancangan Aplikasi Bercocok Tanam," EMITOR J. Tek. Elektro, doi: 10.23917/emitor.v22i1.15136.',
    '[17] T. Yu, L. Mahe, Y. Li, X. Wei, X. Deng, and D. Zhang, "Benefits of Crop Rotation on Climate Resilience and Its Prospects in China," Agronomy, vol. 12, no. 2, pp. 1-18, 2022, doi: 10.3390/agronomy12020436.',
    '[18] R. Sahrial and B. Muslim, "Aplikasi Informasi Gempa Menggunakan Data Terbuka BMKG," Media J. Inform., vol. 15, no. 1, p. 49, 2023, doi: 10.35194/mji.v15i1.3212.',
    '[19] H. Diansyah and S. Syafrinal, "Design and Development of a Mobile Application Using Android Studio and Flutter," J. Mob. Technol., vol. 3, no. 2, pp. 69-76, 2025, doi: 10.59431/jms.v3i2.646.',
    '[20] H. F. Herdiyatmoko, "Desain Sistem Backend Berbasis Rest Api Menggunakan Framework Laravel 7," Skanika, vol. 5, no. 2, pp. 136-144, 2022, doi: 10.36080/skanika.v5i2.2947.',
    '[21] R. Rombach, A. Blattmann, D. Lorenz, P. Esser, and P. Ommer, "High-Resolution Image Synthesis with Latent Diffusion Models," Proc. IEEE CVPR, pp. 10674-10685, 2022, doi: 10.1109/CVPR52688.2022.01042.',
    '[22] L. Mu et al., "DenseLoRA: Dense Low-Rank Adaptation of Large Language Models," Proc. ACL, vol. 1, pp. 10198-10211, 2025, doi: 10.18653/v1/2025.acl-long.503.',
    '[23] S. Tilley, Systems Analysis and Design, 12th ed. Cengage Learning, 2020.',
    '[24] P. P. S. Chen, "The Entity-Relationship Model - toward a Unified View of Data," ACM Trans. Database Syst., vol. 1, no. 1, pp. 9-36, 1976, doi: 10.1145/320434.320440.',
    '[25] H. R. I. Fikri and A. Voutama, "Pengujian Black Box Pada Aplikasi Database Perguruan Tinggi dengan Teknik Equivalence Partitions," ANTIVIRUS J. Ilm. Tek. Inf., vol. 17, no. 1, pp. 1-18, 2023, doi: 10.35457/antivirus.v17i1.2501.',
    '[26] M. Y. Loso Judijanto et al., Metodologi Research and Development: Teori dan Penerapan Metodologi RnD. PT Sonpedia Publishing Indonesia, 2024.',
    '[27] A. Perdana, S. Dewi, N. A. Farhana, and D. Febrian, "Comparative Analysis of SDLC and R&D Methods in System Development: A Case Study of Integrity Zone Management System," Sinkron, vol. 9, no. 4, pp. 3197-3209, 2025, doi: 10.33395/sinkron.v9i4.15337.',
]
for ref in references:
    add_reference(doc, ref)

doc.core_properties.title = "Artikel Ilmiah TaniAdaptif"
doc.core_properties.subject = "Artikel ilmiah berdasarkan skripsi TaniAdaptif"
doc.core_properties.author = "Gaus Abdul Rozak"
doc.core_properties.comments = "Dokumen baru; SKRIPSI.docx sumber tidak diubah."
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
