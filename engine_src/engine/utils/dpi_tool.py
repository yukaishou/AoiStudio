
class DPITool:
    def __init__(self,game_size,screen_size):
        self.LOGIC_W, self.LOGIC_H = game_size[0], game_size[1] # 你开发时用的逻辑分辨率
        self.SCREEN_W, self.SCREEN_H = screen_size[0], screen_size[1]

        # 计算缩放比（取最小值，保证完整显示，不裁剪，保持比例）
        self.SCALE = min(self.SCREEN_W / self.LOGIC_W, self.SCREEN_H / self.LOGIC_H)
        # 计算居中的偏移量（用于贴黑边）
        self.OFFSET_X = (self.SCREEN_W - self.LOGIC_W * self.SCALE) // 2
        self.OFFSET_Y = (self.SCREEN_H - self.LOGIC_H * self.SCALE) // 2
        print(self.SCALE)

        # 【工具函数】逻辑坐标 -> 物理坐标（位置）
    def to_real(self,x, y):
            return int(x * self.SCALE + self.OFFSET_X), int(y * self.SCALE + self.OFFSET_Y)

        # 【工具函数】逻辑尺寸 -> 物理尺寸（大小）
    def to_real_size(self,size):
            return [float(size[0] * self.SCALE),float(size[1] * self.SCALE)]