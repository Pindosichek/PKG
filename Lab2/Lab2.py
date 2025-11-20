import streamlit as st
import os
import pandas as pd
from PIL import Image, TiffTags
from datetime import datetime
import tempfile
import io

st.set_page_config(
    page_title="Image Info Analyzer",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .file-table {
        width: 100%;
        border-collapse: collapse;
    }
    .file-table th, .file-table td {
        padding: 8px 12px;
        border: 1px solid #ddd;
        text-align: left;
    }
    .file-table th {
        background-color: #f0f0f0;
        font-weight: bold;
    }
    .file-table tr:hover {
        background-color: #f5f5f5;
    }
    .error-row {
        background-color: #ffe6e6 !important;
    }
</style>
""", unsafe_allow_html=True)

class ImageInfoExtractor:
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.bmp', '.png', '.pcx'}
    
    def get_image_info(self, file_path):
        """Извлекает информацию об изображении"""
        try:
            with Image.open(file_path) as img:
                file_stats = os.stat(file_path)
                actual_file_size = file_stats.st_size
                
                info = {
                    'filename': os.path.basename(file_path),
                    'filepath': file_path,
                    'format': img.format or 'Unknown',
                    'width': img.size[0],
                    'height': img.size[1],
                    'size_str': f"{img.size[0]} × {img.size[1]}",
                    'mode': img.mode,
                    'color_depth': self.get_color_depth(img),
                    'dpi': self.get_dpi(img),
                    'compression': self.get_compression(img, file_path, actual_file_size),
                    'file_size_mb': f"{actual_file_size / 1024 / 1024:.2f}",
                    'error': None
                }
                return info
        except Exception as e:
            return {
                'filename': os.path.basename(file_path),
                'filepath': file_path,
                'error': str(e),
                'format': 'Error',
                'size_str': 'Error',
                'dpi': 'Error',
                'color_depth': 'Error',
                'compression': 'Error',
                'file_size_mb': 'Error'
            }
    
    def get_color_depth(self, img):
        """Определяет глубину цвета"""
        mode_bits = {
            '1': 1, 'L': 8, 'P': 8, 'RGB': 24, 'RGBA': 32,
            'CMYK': 32, 'YCbCr': 24, 'LAB': 24, 'HSV': 24, 'I': 32, 'F': 32
        }
        return mode_bits.get(img.mode, f"Unknown ({img.mode})")
    
    def get_dpi(self, img):
        dpi = img.info.get('dpi', (72, 72))
        if isinstance(dpi, tuple) and len(dpi) == 2:
            return f"{dpi[0]} × {dpi[1]}"
        return "72 × 72"
    
    def calculate_jpeg_compression_ratio(self, img, actual_file_size):
        """Вычисляет на сколько процентов сжато JPEG изображение"""
        try:
            # Создаем несжатое BMP в памяти для сравнения
            with io.BytesIO() as buffer:
                # Конвертируем в RGB если нужно (JPEG не поддерживает прозрачность)
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = img.convert('RGB')
                else:
                    rgb_img = img
                
                # Сохраняем как несжатый BMP в память
                rgb_img.save(buffer, format='BMP')
                uncompressed_size = buffer.tell()
                
                # Вычисляем на сколько процентов сжато
                if uncompressed_size > 0:
                    compression_percentage = ((uncompressed_size - actual_file_size) / uncompressed_size) * 100
                    return f"{compression_percentage:.1f}%"
                else:
                    return "N/A"
                    
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_compression(self, img, file_path, actual_file_size):
        """Получает информацию о сжатии"""
        # Для JPEG файлов - вычисляем на сколько процентов сжато
        if img.format == 'JPEG':
            return self.calculate_jpeg_compression_ratio(img, actual_file_size)
        
        # Для PNG файлов - всегда 0% (без сжатия)
        elif img.format == 'PNG':
            return "0%"
        
        # Для BMP файлов - всегда 0% (без сжатия)
        elif img.format == 'BMP':
            return "0%"
        
        # Для TIFF файлов
        elif img.format == 'TIFF':
            compression = img.info.get('compression', 'None')
            compression_map = {
                'jpeg': 'JPEG', 'deflate': 'DEFLATE', 'packbits': 'PackBits',
                'lzw': 'LZW', 'none': 'None', 'raw': 'RAW', 'tiff_lzw': 'TIFF LZW'
            }
            return compression_map.get(str(compression).lower(), str(compression).capitalize())
        
        # Для GIF файлов
        elif img.format == 'GIF':
            return 'LZW'
        
        # Для других форматов
        else:
            compression = img.info.get('compression', 'None')
            if compression != 'None':
                return str(compression).capitalize()
            else:
                return 'Unknown'

def scan_folder(folder_path):
    """Сканирует папку и находит все изображения"""
    image_files = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if os.path.splitext(file)[1].lower() in {'.jpg', '.jpeg', '.gif', '.tif', '.tiff', '.bmp', '.png', '.pcx'}:
                image_files.append(os.path.join(root, file))
        
        if len(image_files) >= 100000:
            break
    
    return image_files[:100000]

def main():
    st.markdown('<div class="main-header">Анализатор графических файлов</div>', unsafe_allow_html=True)
    
    if 'extractor' not in st.session_state:
        st.session_state.extractor = ImageInfoExtractor()
    
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    
    if 'folder_path' not in st.session_state:
        st.session_state.folder_path = ""
 
    with st.sidebar:
        st.header("Выбор папки")
        
        folder_path = st.text_input(
            "Введите путь к папке:",
            value=st.session_state.folder_path,
            placeholder="C:/Users/Name/Pictures или /home/user/images"
        )
        
        if st.button("Сканировать папку", type="primary"):
            if folder_path and os.path.exists(folder_path):
                st.session_state.folder_path = folder_path
                scan_and_process_folder(folder_path)
            else:
                st.error("Указанная папка не существует!")
        
        st.markdown("---")
        st.info("""
        **Поддерживаемые форматы:**
        - JPEG, GIF, TIFF, BMP, PNG, PCX
        
        **Отображаемая информация:**
        - Имя файла, размер, разрешение
        - Глубина цвета, степень сжатия
        - Для JPEG: на сколько % сжато
        - Для PNG и BMP: 0% (без сжатия)
        """)

    if st.session_state.processed_files:
        display_results()
    else:
        show_welcome()

def scan_and_process_folder(folder_path):
    """Сканирует и обрабатывает папку"""
    with st.spinner("Сканирование папки..."):
        image_files = scan_folder(folder_path)
        
        if not image_files:
            st.error("В указанной папке не найдено изображений!")
            return
        
        st.info(f"Найдено файлов: {len(image_files)}")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_data = []
        
        for i, file_path in enumerate(image_files):
            progress = (i + 1) / len(image_files)
            progress_bar.progress(progress)
            status_text.text(f"Обработка {i+1}/{len(image_files)}: {os.path.basename(file_path)}")
            info = st.session_state.extractor.get_image_info(file_path)
            processed_data.append(info)
        
        progress_bar.empty()
        status_text.text(f"Обработано файлов: {len(processed_data)}")
        
        st.session_state.processed_files = processed_data

def display_results():
    data = st.session_state.processed_files

    total_files = len(data)
    successful = len([f for f in data if not f.get('error')])
    error_count = total_files - successful
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего файлов", total_files)
    with col2:
        st.metric("Успешно", successful)
    with col3:
        st.metric("Ошибки", error_count)

    search_term = st.text_input("Поиск по имени файла:", placeholder="Введите часть имени файла...")
    
    filtered_data = data
    if search_term:
        filtered_data = [f for f in data if search_term.lower() in f['filename'].lower()]

    display_data = []
    for file_info in filtered_data:
        display_data.append({
            'Файл': file_info['filename'],
            'Размер (пиксели)': file_info['size_str'],
            'Разрешение (DPI)': file_info['dpi'],
            'Глубина цвета': file_info['color_depth'],
            'Сжатие': file_info['compression'],
            'Формат': file_info['format'],
            'Размер файла (MB)': file_info['file_size_mb'],
            'Статус': 'Ошибка' if file_info.get('error') else 'OK'
        })
    
    if display_data:
        df = pd.DataFrame(display_data)
 
        def color_rows(row):
            if row['Статус'] == 'Ошибка':
                return ['background-color: #ffe6e6'] * len(row)
            return [''] * len(row)
        
        styled_df = df.style.apply(color_rows, axis=1)
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600
        )
        
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="Экспорт в CSV",
            data=csv,
            file_name=f"image_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Файлы не найдены")

def show_welcome():
    """Показывает приветственный экран"""
    st.markdown("""
    ## Анализатор графических файлов
    
    Это приложение позволяет анализировать графические файлы и извлекать из них основную информацию.
    
    ### Поддерживаемые форматы:
    - **JPEG/JPG** - формат сжатия с потерями (показывает на сколько % сжато)
    - **GIF** - поддерживает анимацию и палитру
    - **TIFF** - высококачественный формат с тегами
    - **BMP** - несжатый формат Windows (0% сжатия)
    - **PNG** - сжатие без потерь с прозрачностью (0% сжатия)
    - **PCX** - формат ZSoft Paintbrush
    
    ### Извлекаемая информация:
    - **Имя файла** - название файла
    - **Размер изображения** - ширина и высота в пикселях
    - **Разрешение** - плотность точек на дюйм (DPI)
    - **Глубина цвета** - количество бит на пиксель
    - **Сжатие** - на сколько процентов сжато изображение
    
    ### Как использовать:
    1. Введите путь к папке в боковой панели
    2. Нажмите кнопку "Сканировать папку"
    3. Просматривайте результаты в таблице
    4. Используйте поиск для фильтрации файлов
    
    ### Особенности:
    - Быстрая обработка тысяч файлов
    - Удобное табличное представление
    - Поиск и фильтрация результатов
    - Экспорт данных в CSV
    """)

if __name__ == "__main__":
    main()