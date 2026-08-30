"""
CFG 错误处理模块 - 提供增强的错误定位和提示功能
"""

from dataclasses import dataclass
from typing import Optional
from engine_src.engine.core import log


@dataclass
class CFGError:
    """CFG 错误信息类"""
    line_number: int
    column: int
    message: str
    error_type: str = "ERROR"  # ERROR, WARNING, INFO
    context: Optional[str] = None
    
    def __str__(self):
        loc = f"第{self.line_number}行"
        if self.column > 0:
            loc += f"第{self.column}列"
        
        type_tag = {
            "ERROR": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }.get(self.error_type, "❓")
        
        msg = f"[CFG {type_tag}] {loc}: {self.message}"
        if self.context:
            msg += f"\n  上下文: {self.context}"
        return msg


class CFGErrorHandler:
    """CFG 错误处理器"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.current_line = 0
        self.current_file = ""
    
    def set_current_location(self, line_number: int, file_path: str = ""):
        """设置当前解析位置"""
        self.current_line = line_number
        self.current_file = file_path
    
    def report_error(self, message: str, line_number: Optional[int] = None,
                    column: int = 0, context: Optional[str] = None):
        """报告错误"""
        line = line_number if line_number is not None else self.current_line
        error = CFGError(
            line_number=line,
            column=column,
            message=message,
            error_type="ERROR",
            context=context
        )
        self.errors.append(error)
        log.log(2, str(error))
        return error
    
    def report_warning(self, message: str, line_number: Optional[int] = None,
                      column: int = 0, context: Optional[str] = None):
        """报告警告"""
        line = line_number if line_number is not None else self.current_line
        warning = CFGError(
            line_number=line,
            column=column,
            message=message,
            error_type="WARNING",
            context=context
        )
        self.warnings.append(warning)
        log.log(1, str(warning))
        return warning
    
    def report_info(self, message: str, line_number: Optional[int] = None,
                   column: int = 0, context: Optional[str] = None):
        """报告信息"""
        line = line_number if line_number is not None else self.current_line
        info = CFGError(
            line_number=line,
            column=column,
            message=message,
            error_type="INFO",
            context=context
        )
        log.log(0, str(info))
        return info
    
    def has_errors(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) > 0
    
    def get_summary(self) -> str:
        """获取错误摘要"""
        if not self.errors and not self.warnings:
            return "✅ CFG 脚本解析成功，无错误"
        
        summary = []
        if self.errors:
            summary.append(f"❌ {len(self.errors)} 个错误")
        if self.warnings:
            summary.append(f"⚠️ {len(self.warnings)} 个警告")
        
        return ", ".join(summary)
    
    def clear(self):
        """清除所有错误记录"""
        self.errors.clear()
        self.warnings.clear()
        self.current_line = 0
        self.current_file = ""
    
    def validate_and_raise(self):
        """如果有错误则抛出异常"""
        if self.has_errors():
            error_msgs = "\n".join(str(e) for e in self.errors)
            raise RuntimeError(f"CFG 脚本包含 {len(self.errors)} 个错误:\n{error_msgs}")
