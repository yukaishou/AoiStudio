"""
CFG 变量管理器 - 提供脚本变量系统支持
"""

import re
from typing import Any, Optional, Dict
from engine_src.engine.core import log


class VariableManager:
    """
    CFG 变量管理器
    
    支持：
    - 设置变量: set var_name value
    - 引用变量: ${var_name}
    - 变量类型自动推断（字符串、整数、浮点数、布尔值）
    """
    
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self._pattern = re.compile(r'\$\{([^}]+)\}')  # 匹配 ${var_name}
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        if not name or not isinstance(name, str):
            raise ValueError(f"无效的变量名: {name}")
        
        # 自动类型转换
        converted_value = self._convert_type(value)
        self.variables[name] = converted_value
        log.log(0, f"[CFG Var] 设置变量 {name} = {converted_value} (type: {type(converted_value).__name__})")
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量值"""
        if name not in self.variables:
            if default is not None:
                return default
            raise KeyError(f"未定义的变量: {name}")
        return self.variables[name]
    
    def has_variable(self, name: str) -> bool:
        """检查变量是否存在"""
        return name in self.variables
    
    def delete_variable(self, name: str):
        """删除变量"""
        if name in self.variables:
            del self.variables[name]
            log.log(0, f"[CFG Var] 删除变量 {name}")
    
    def resolve_variables(self, text: str) -> str:
        """
        解析文本中的变量引用
        示例: "Hello ${name}" -> "Hello World"
        """
        if not isinstance(text, str):
            return text
        
        def replace_var(match):
            var_name = match.group(1)
            try:
                value = self.get_variable(var_name)
                return str(value)
            except KeyError:
                log.log(2, f"[CFG Var] 未定义变量: {var_name}")
                return match.group(0)  # 保持原样
        
        return self._pattern.sub(replace_var, text)
    
    @staticmethod
    def _convert_type(value: Any) -> Any:
        """
        自动类型转换
        - "true"/"false" -> bool
        - 纯数字字符串 -> int 或 float
        - 其他 -> str
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_val = value.lower().strip()
            
            # 布尔值
            if lower_val in ('true', 'yes', '1'):
                return True
            if lower_val in ('false', 'no', '0'):
                return False
            
            # 整数
            try:
                return int(value)
            except ValueError:
                pass
            
            # 浮点数
            try:
                return float(value)
            except ValueError:
                pass
        
        return value
    
    def evaluate_expression(self, expr: str) -> Any:
        """
        简单的表达式求值（支持基本运算）
        示例: "${a} + ${b}", "${x} > 10"
        """
        resolved = self.resolve_variables(expr)
        
        # 尝试作为 Python 表达式求值（安全限制）
        try:
            # 只允许安全的操作符和数字
            safe_pattern = re.compile(r'^[\d\s\+\-\*\/\(\)\<\>\=\!\.]+$')
            if safe_pattern.match(resolved):
                return eval(resolved)
        except Exception as e:
            log.log(2, f"[CFG Var] 表达式求值失败: {expr}, 错误: {e}")
        
        return resolved
