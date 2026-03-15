import io
from docx import Document
from typing import Optional

class FileProcessor:
    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> Optional[str]:
        """
        根据文件扩展名提取文本内容
        支持: .docx, .txt, .md
        """
        ext = filename.split('.')[-1].lower()
        
        try:
            if ext == 'docx':
                # 处理 Word 文档
                doc = Document(io.BytesIO(file_content))
                full_text = []
                for para in doc.paragraphs:
                    full_text.append(para.text)
                return '\n'.join(full_text)
            
            elif ext in ['txt', 'md']:
                # 处理 纯文本或 Markdown
                return file_content.decode('utf-8')
            
            else:
                # 不支持的格式
                return None
                
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            # 尝试回退到 latin-1 或者其他编码可能性（针对 txt）
            if ext in ['txt', 'md']:
                try:
                    return file_content.decode('gbk')
                except:
                    pass
            return None

file_processor = FileProcessor()
