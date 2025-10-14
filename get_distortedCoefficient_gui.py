import cv2
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from tempMatcher import TemplateMatcher
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os

class Get_distort_coefficient:
    def __init__(self, gary_image, template, pixel_size, check_size_designed=40, threshold=0.9, iou_threshold=0.4):
        self.Gary_image = gary_image
        self.Temp_image = template
        self.check_size_designed = check_size_designed
        self.pixel_size = pixel_size
        self.threshold = threshold
        self.iou_threshold = iou_threshold
        self.Iamge_Height = gary_image.shape[0]
        self.Iamge_Width = gary_image.shape[1]
        self.Temp_Height = template.shape[0]
        self.Temp_Width = template.shape[1]

    def dev_function(self, pixel_position, a, b, c):
        """
        定义畸变函数，使用三次多项式拟合
        :param pixel_position: 相机像素位置
        :param a: 三次项系数，为畸变系数
        :param b: 二次项系数，相机画幅中心于物镜成像中心的固定偏置
        :param c: 一次项系数，模板匹配的容差，与硬件无关
        :return: 畸变值造成的像素偏差值
        """
        dev = a * (pixel_position - b) ** 3 + c
        return dev
    
    
    def get_distorted_Coeffi(self, posi_camera, posi_ideal):
        """
        使用 curve_fit 进行拟合，并打印结果
        """
        dev = posi_camera - posi_ideal
        popt, pcov = curve_fit(self.dev_function, posi_camera, dev)
        print("拟合参数:")
        print("a =", popt[0])
        print("b =", popt[1])
        return popt
    
    def work(self):
        """
        通过模板匹配的方式获得格子中心，求取真实(ideal)像素位置和相机(camera)像素位置的相对偏差
        """
        # TODO: 进行模板匹配
        # 初始化模板匹配器
        matcher = TemplateMatcher(threshold=self.threshold, iou_threshold=self.iou_threshold)
        # 执行匹配, 返回检测到的矩形框和目标中心像素坐标
        rects, df = matcher.match(self.Gary_image, self.Temp_image)
        
        # 绘制结果到图像上（不保存文件）
        result_image = self.Gary_image.copy()
        print(f"原始图像尺寸: {result_image.shape}")
        
        # 如果是灰度图则转换为彩色
        if len(result_image.shape) == 2:
            result_image = cv2.cvtColor(result_image, cv2.COLOR_GRAY2BGR)
        
        # 绘制匹配到的矩形框和中心点
        for rect in rects:
            x, y, w, h = rect
            # 确保坐标是整数且在图像范围内
            x, y, w, h = int(x), int(y), int(w), int(h)
            
            # 计算中心点坐标
            center_x = int(round(x + w/2.0))
            center_y = int(round(y + h/2.0))
            
            # 确保矩形坐标在图像范围内
            x1 = max(0, min(x, result_image.shape[1]-1))
            y1 = max(0, min(y, result_image.shape[0]-1))
            x2 = max(0, min(x + w, result_image.shape[1]-1))
            y2 = max(0, min(y + h, result_image.shape[0]-1))
            
            # 绘制矩形框（蓝色）
            cv2.rectangle(result_image, (x1, y1), (x2, y2), (255, 0, 0), 2)
            
            # 绘制中心点（绿色圆点）
            cv2.circle(result_image, (center_x, center_y), 3, (0, 255, 0), -1)
            
            print(f"绘制矩形: ({x1}, {y1}) -> ({x2}, {y2}), 中心点: ({center_x}, {center_y})")
        
        print(f"绘制矩形后的图像尺寸: {result_image.shape}")
        print(f"总共绘制了 {len(rects)} 个匹配矩形和中心点")
        
        # 保存匹配结果图像到文件
        cv2.imwrite('results.jpg', result_image)
        print("匹配结果已保存到 results.jpg")
        
        # TODO: 计算实际像素坐标和理论像素坐标
        # 图像中心置为零点：中心的畸变量最小
        df['posi_camera'] = df['center_x'] - 0.5*self.Iamge_Width
        # 计算以图像中心为零点的理论像素坐标：根据像素比及标片的设计尺寸反算理论位置
        df['posi_ideal'] = self.check_size_designed/self.pixel_size * df.index
        # 将两者的中心位置对齐
        index_closest = df['posi_camera'].abs().idxmin() 
        offset_ = df.loc[index_closest, 'posi_ideal'] - df.loc[index_closest, 'posi_camera']
        df['posi_ideal'] -= offset_ 
        
        posi_camera = df['posi_camera'].to_numpy()
        posi_ideal = df['posi_ideal'].to_numpy()
        
        # TODO: 计算畸变系数
        distorted_Coeffi = self.get_distorted_Coeffi(posi_camera, posi_ideal)
        dev_fit = self.dev_function(posi_camera, distorted_Coeffi[0], distorted_Coeffi[1], distorted_Coeffi[2])
        
        # 创建畸变曲线图并保存到文件
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(posi_camera, dev_fit, label='dev_fitted', linewidth=2)
        ax.plot(posi_camera, posi_camera-posi_ideal, ".", label='dev_measured', markersize=8)
        ax.set_ylabel('dev (posi_camera - posi_ideal)')
        ax.set_xlabel('pixel position of camera')
        ax.legend()
        ax.grid(True)
        
        # 保存畸变曲线图到文件
        plt.savefig('fitting_curve.jpg', bbox_inches='tight', dpi=300)
        print("畸变曲线已保存到 fitting_curve.jpg")
        
        # 将matplotlib图形转换为PIL图像（用于返回）
        fig.canvas.draw()
        img_data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img_data = img_data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        fitting_image = Image.fromarray(img_data)
        print(f"畸变曲线图像尺寸: {fitting_image.size}")
        plt.close(fig)
        
        print(f"返回结果: result_image shape={result_image.shape}, fitting_image size={fitting_image.size}")
        return dev_fit, posi_camera-posi_ideal, distorted_Coeffi, df, result_image, fitting_image

class ROISelector:
    def __init__(self, canvas, image, status_callback=None):
        self.canvas = canvas
        self.image = image
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.roi_coords = None
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.status_callback = status_callback
        
        # 绑定鼠标事件
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
    def set_canvas_offset(self, offset_x, offset_y):
        """设置画布偏移量，用于坐标转换"""
        self.canvas_offset_x = offset_x
        self.canvas_offset_y = offset_y
        
    def on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
    
    def on_mouse_drag(self, event):
        if self.start_x is not None:
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline="red", width=2
            )
    
    def on_mouse_up(self, event):
        if self.start_x is not None:
            if self.rect_id:
                x1, y1, x2, y2 = self.canvas.coords(self.rect_id)
                # 确保坐标顺序正确
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                self.roi_coords = (int(x1), int(y1), int(x2), int(y2))
                print(f"ROI selected: {self.roi_coords}")
            else:
                # 如果没有矩形，创建一个最小的ROI区域
                x1, y1 = self.start_x, self.start_y
                x2, y2 = event.x, event.y
                x1, x2 = min(x1, x2), max(x1, x2)
                y1, y2 = min(y1, y2), max(y1, y2)
                self.roi_coords = (int(x1), int(y1), int(x2), int(y2))
                print(f"ROI selected (no rect): {self.roi_coords}")
            
            # 调用状态更新回调
            if self.status_callback:
                self.status_callback()
        
        # 重置起始点
        self.start_x = None
        self.start_y = None
    
    def get_roi_coords(self):
        return self.roi_coords
    
    def clear_roi(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        self.roi_coords = None
        # 调用状态更新回调
        if self.status_callback:
            self.status_callback()

class DistortionCoefficientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("畸变系数计算器")
        self.root.geometry("1200x700")
        
        # 变量
        self.img_path = tk.StringVar()
        self.check_size = tk.DoubleVar(value=40.0)
        self.pixel_size = tk.DoubleVar(value=0.714268)
        self.threshold = tk.DoubleVar(value=0.9)  # 模板匹配阈值
        self.iou_threshold = tk.DoubleVar(value=0.4)  # IOU阈值
        self.original_image = None
        self.template_image = None
        self.roi_selector = None
        self.scale_factor = 1.0
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        
        # 性能优化：添加缩放缓存和节流
        self.scaled_image_cache = {}  # 缓存不同缩放比例的图像
        self.last_scale_update = 0    # 上次缩放更新时间
        self.scale_update_delay = 50  # 缩放更新延迟（毫秒）
        self.scale_timer_id = None    # 缩放定时器ID
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 左侧控制面板
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(left_frame, text="文件选择", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(file_frame, text="图像文件:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(file_frame, textvariable=self.img_path, width=40).grid(row=0, column=1, padx=(5, 5))
        ttk.Button(file_frame, text="浏览", command=self.browse_img).grid(row=0, column=2)
        
        # 参数设置区域
        param_frame = ttk.LabelFrame(left_frame, text="参数设置", padding="10")
        param_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(param_frame, text="标片设计尺寸 (μm):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(param_frame, textvariable=self.check_size, width=15).grid(row=0, column=1, padx=(5, 0))
        
        ttk.Label(param_frame, text="像素尺寸 (μm/pix):").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(param_frame, textvariable=self.pixel_size, width=15).grid(row=1, column=1, padx=(5, 0), pady=(10, 0))
        
        # 添加模板匹配参数
        ttk.Label(param_frame, text="匹配阈值 (threshold):").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(param_frame, textvariable=self.threshold, width=15).grid(row=2, column=1, padx=(5, 0), pady=(10, 0))
        
        ttk.Label(param_frame, text="IOU阈值 (iou_threshold):").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(param_frame, textvariable=self.iou_threshold, width=15).grid(row=3, column=1, padx=(5, 0), pady=(10, 0))
        
        # 添加参数说明
        ttk.Label(param_frame, text="匹配阈值: 0.0-1.0，值越大匹配越严格", 
                 font=("Arial", 8), foreground="gray").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        ttk.Label(param_frame, text="IOU阈值: 0.0-1.0，值越大重叠检测越严格", 
                 font=("Arial", 8), foreground="gray").grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        # ROI选择说明
        roi_frame = ttk.LabelFrame(left_frame, text="ROI选择", padding="10")
        roi_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(roi_frame, text="在右侧图像上拖拽选择ROI区域作为模板", 
                 wraplength=250).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # 添加ROI状态显示
        self.roi_status_label = ttk.Label(roi_frame, text="未选择ROI", foreground="red")
        self.roi_status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(roi_frame, text="清除ROI", command=self.clear_roi).grid(row=2, column=0, padx=(0, 5))
        ttk.Button(roi_frame, text="确认ROI", command=self.confirm_roi).grid(row=2, column=1)
        
        # 控制按钮
        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=3, column=0, pady=(0, 10))
        
        ttk.Button(control_frame, text="开始计算", command=self.calculate, style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(control_frame, text="清空结果", command=self.clear_results).pack(side=tk.LEFT)
        
        # 结果显示区域
        result_frame = ttk.LabelFrame(left_frame, text="计算结果", padding="10")
        result_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建文本显示区域
        self.result_text = tk.Text(result_frame, height=15, width=45)
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 右侧图像预览区域
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 图像预览区域
        preview_frame = ttk.LabelFrame(right_frame, text="图像预览 (滚轮缩放，右键拖动，拖拽选择ROI)", padding="10")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 创建画布用于显示图像
        self.canvas = tk.Canvas(preview_frame, width=600, height=500, bg="white")
        self.canvas.pack(expand=True, fill=tk.BOTH)
        
        # 绑定滚轮事件
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-2>", self.on_middle_click)
        
        # 添加右键拖动功能
        self.canvas.bind("<Button-3>", self.on_right_mouse_down)  # 右键按下
        self.canvas.bind("<B3-Motion>", self.on_right_mouse_drag)  # 右键拖动
        self.canvas.bind("<ButtonRelease-3>", self.on_right_mouse_up)  # 右键释放
        
        # 拖动相关变量
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_offset_x = 0
        self.drag_start_offset_y = 0
        
        # 结果查看按钮区域
        result_buttons_frame = ttk.LabelFrame(right_frame, text="结果查看", padding="10")
        result_buttons_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 创建按钮框架
        buttons_frame = ttk.Frame(result_buttons_frame)
        buttons_frame.pack(expand=True, fill=tk.BOTH)
        
        # 左侧按钮
        left_buttons_frame = ttk.Frame(buttons_frame)
        left_buttons_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 5))
        
        ttk.Button(left_buttons_frame, text="打开匹配结果", 
                  command=lambda: self.open_result_file('results.jpg')).pack(expand=True, fill=tk.BOTH, pady=2)
        
        # 右侧按钮
        right_buttons_frame = ttk.Frame(buttons_frame)
        right_buttons_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=(5, 0))
        
        ttk.Button(right_buttons_frame, text="打开畸变曲线", 
                  command=lambda: self.open_result_file('fitting_curve.jpg')).pack(expand=True, fill=tk.BOTH, pady=2)
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(4, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        result_buttons_frame.columnconfigure(0, weight=1)
        result_buttons_frame.rowconfigure(0, weight=1)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.rowconfigure(0, weight=1)
        left_buttons_frame.columnconfigure(0, weight=1)
        left_buttons_frame.rowconfigure(0, weight=1)
        right_buttons_frame.columnconfigure(0, weight=1)
        right_buttons_frame.rowconfigure(0, weight=1)
        
        # 初始化结果预览区域
        # 不再需要初始化结果预览区域

    def on_mouse_wheel(self, event):
        """滚轮缩放（优化版本）"""
        if self.original_image is not None:
            # 应用缩放
            old_scale = self.scale_factor
            if event.delta > 0:
                self.scale_factor *= 1.1
            else:
                self.scale_factor /= 1.1
            
            # 限制缩放范围，确保图像不会完全消失
            min_scale = max(0.05, 50.0 / max(self.original_image.size))
            max_scale = 10.0
            self.scale_factor = max(min_scale, min(max_scale, self.scale_factor))
            
            # 如果缩放比例没有变化，不更新显示
            if abs(self.scale_factor - old_scale) < 0.001:
                return
            
            # 取消之前的定时器
            if self.scale_timer_id:
                self.root.after_cancel(self.scale_timer_id)
            
            # 设置新的定时器，延迟更新显示（节流）
            self.scale_timer_id = self.root.after(self.scale_update_delay, self.deferred_scale_update)
    
    def deferred_scale_update(self):
        """延迟的缩放更新（节流机制）"""
        self.scale_timer_id = None
        print(f"执行缩放更新: {self.scale_factor:.3f}")
        self.update_image_display()
    
    def on_middle_click(self, event):
        """中键重置缩放"""
        if self.original_image is not None:
            old_scale = self.scale_factor
            self.scale_factor = 1.0
            if abs(self.scale_factor - old_scale) > 0.001:
                print(f"重置缩放: {old_scale:.3f} -> {self.scale_factor:.3f}")
                self.update_image_display()
    
    def on_right_mouse_down(self, event):
        """右键按下"""
        if self.original_image is not None:
            self.dragging = True
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.drag_start_offset_x = self.canvas_offset_x
            self.drag_start_offset_y = self.canvas_offset_y
            print(f"右键按下: 起始位置({event.x}, {event.y}), 起始偏移量({self.drag_start_offset_x}, {self.drag_start_offset_y})")
    
    def on_right_mouse_drag(self, event):
        """右键拖动"""
        if self.dragging and self.original_image is not None:
            # 计算新的偏移量
            delta_x = event.x - self.drag_start_x
            delta_y = event.y - self.drag_start_y
            
            new_offset_x = self.drag_start_offset_x + delta_x
            new_offset_y = self.drag_start_offset_y + delta_y
            
            # 限制拖动范围，防止图像完全移出画布
            canvas_width = 600
            canvas_height = 500
            img_width = int(self.original_image.size[0] * self.scale_factor)
            img_height = int(self.original_image.size[1] * self.scale_factor)
            
            # 计算最大可拖动范围
            max_offset_x = max(0, img_width - canvas_width)
            max_offset_y = max(0, img_height - canvas_height)
            
            # 限制偏移量范围
            new_offset_x = max(-max_offset_x, min(0, new_offset_x))
            new_offset_y = max(-max_offset_y, min(0, new_offset_y))
            
            # 更新偏移量
            self.canvas_offset_x = new_offset_x
            self.canvas_offset_y = new_offset_y
            
            # 更新ROI选择器的偏移量
            if self.roi_selector:
                self.roi_selector.set_canvas_offset(self.canvas_offset_x, self.canvas_offset_y)
            
            # 重新绘制图像（不重新缩放，只改变位置）
            self.redraw_image_at_current_position()
    
    def on_right_mouse_up(self, event):
        """右键释放"""
        if self.dragging:
            self.dragging = False
            print(f"右键释放: 最终偏移量({self.canvas_offset_x}, {self.canvas_offset_y})")
    
    def redraw_image_at_current_position(self):
        """在当前位置重新绘制图像（不重新缩放）"""
        if self.original_image is not None:
            # 获取当前缩放后的图像
            img_width, img_height = self.original_image.size
            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)
            
            # 创建缓存键
            cache_key = f"{new_width}x{new_height}_current"
            
            # 检查是否有缓存的图像
            if cache_key in self.scaled_image_cache:
                photo = self.scaled_image_cache[cache_key]
            else:
                # 如果没有缓存，使用现有的缓存逻辑
                if self.scale_factor >= 1.0:
                    resampling_method = Image.Resampling.LANCZOS
                elif new_width > 2000 or new_height > 2000:
                    resampling_method = Image.Resampling.BICUBIC
                elif new_width > 1000 or new_height > 1000:
                    resampling_method = Image.Resampling.BILINEAR
                else:
                    resampling_method = Image.Resampling.LANCZOS
                
                scaled_image = self.original_image.resize((new_width, new_height), resampling_method)
                photo = ImageTk.PhotoImage(scaled_image)
                self.scaled_image_cache[cache_key] = photo
            
            # 清除画布并重新绘制
            self.canvas.delete("all")
            self.canvas.create_image(self.canvas_offset_x, self.canvas_offset_y, anchor=tk.NW, image=photo)
            self.canvas.image = photo
            
            # 显示调试信息
            self.canvas.create_text(10, 10, text=f"缩放: {self.scale_factor:.2f}x (拖动中)", 
                                  fill="red", font=("Arial", 12), anchor=tk.NW)
    
    def update_image_display(self):
        """更新图像显示（优化版本）"""
        if self.original_image is not None:
            # 计算缩放后的尺寸
            img_width, img_height = self.original_image.size
            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)
            
            # 优化重采样策略：根据缩放比例和图像大小选择合适的方法
            if self.scale_factor >= 1.0:
                # 放大时使用高质量插值
                resampling_method = Image.Resampling.LANCZOS
                quality_suffix = "_hq"
            elif new_width > 2000 or new_height > 2000:
                # 超大图像时使用中等质量插值
                resampling_method = Image.Resampling.BICUBIC
                quality_suffix = "_mq"
            elif new_width > 1000 or new_height > 1000:
                # 大图像时使用中等质量插值
                resampling_method = Image.Resampling.BILINEAR
                quality_suffix = "_mq"
            else:
                # 小图像时使用高质量插值
                resampling_method = Image.Resampling.LANCZOS
                quality_suffix = "_hq"
            
            # 创建包含质量信息的缓存键
            cache_key = f"{new_width}x{new_height}{quality_suffix}"
            
            if cache_key in self.scaled_image_cache:
                print(f"使用缓存图像: {cache_key}")
                photo = self.scaled_image_cache[cache_key]
            else:
                print(f"缩放信息: 原始尺寸={img_width}x{img_height}, 缩放比例={self.scale_factor:.3f}, 新尺寸={new_width}x{new_height}")
                print(f"使用重采样方法: {resampling_method}")
                
                # 调整图像大小
                scaled_image = self.original_image.resize((new_width, new_height), resampling_method)
                photo = ImageTk.PhotoImage(scaled_image)
                
                # 缓存结果（限制缓存大小）
                if len(self.scaled_image_cache) > 15:  # 增加缓存大小以容纳不同质量级别
                    # 删除最旧的缓存项
                    oldest_key = next(iter(self.scaled_image_cache))
                    del self.scaled_image_cache[oldest_key]
                
                self.scaled_image_cache[cache_key] = photo
                print(f"图像已缓存: {cache_key}")
            
            # 更新画布
            self.canvas.delete("all")
            
            # 计算居中位置，确保图像始终在画布内可见
            canvas_width = 600
            canvas_height = 500
            
            # 计算偏移量，确保图像不会超出画布边界
            if new_width >= canvas_width:
                self.canvas_offset_x = (canvas_width - new_width) // 2
            else:
                self.canvas_offset_x = (canvas_width - new_width) // 2
            
            if new_height >= canvas_height:
                self.canvas_offset_y = (canvas_height - new_height) // 2
            else:
                self.canvas_offset_y = (canvas_height - new_height) // 2
            
            # 确保偏移量不为负数（当图像很大时）
            self.canvas_offset_x = max(0, self.canvas_offset_x)
            self.canvas_offset_y = max(0, self.canvas_offset_y)
            
            print(f"画布偏移量: ({self.canvas_offset_x}, {self.canvas_offset_y})")
            
            # 在画布上显示图像
            self.canvas.create_image(self.canvas_offset_x, self.canvas_offset_y, anchor=tk.NW, image=photo)
            self.canvas.image = photo  # 保持引用
            
            # 更新ROI选择器的画布偏移量
            if self.roi_selector:
                self.roi_selector.set_canvas_offset(self.canvas_offset_x, self.canvas_offset_y)
            
            # 添加调试信息：在画布上显示当前缩放比例和重采样方法
            quality_text = "高质量" if quality_suffix == "_hq" else "中等质量"
            self.canvas.create_text(10, 10, text=f"缩放: {self.scale_factor:.2f}x ({quality_text})", 
                                  fill="red", font=("Arial", 12), anchor=tk.NW)
        
    def update_roi_status(self):
        """更新ROI状态显示"""
        if self.roi_selector and self.roi_selector.get_roi_coords():
            coords = self.roi_selector.get_roi_coords()
            self.roi_status_label.config(text=f"已选择ROI: ({coords[0]},{coords[1]}) -> ({coords[2]},{coords[3]})", foreground="green")
        else:
            self.roi_status_label.config(text="未选择ROI", foreground="red")
    
    def browse_img(self):
        filename = filedialog.askopenfilename(
            title="选择图像文件",
            filetypes=[("图像文件", "*.bmp *.jpg *.jpeg *.png *.tif *.tiff"), ("所有文件", "*.*")]
        )
        if filename:
            self.img_path.set(filename)
            self.load_and_preview_image(filename)
    
    def load_and_preview_image(self, image_path):
        try:
            # 清理之前的缓存
            self.scaled_image_cache.clear()
            print("图像缓存已清理")
            
            # 读取图像
            self.original_image = Image.open(image_path)
            
            # 计算合适的初始缩放比例，让图像填满画幅
            canvas_width = 600
            canvas_height = 500
            img_width, img_height = self.original_image.size
            
            # 计算适合画布的缩放比例，让图像填满画幅
            scale_x = canvas_width / img_width
            scale_y = canvas_height / img_height
            
            # 选择较大的缩放比例，让图像填满画幅（可能超出部分会被裁剪）
            self.scale_factor = max(scale_x, scale_y)
            
            print(f"图像加载: 原始尺寸={img_width}x{img_height}, 画布尺寸={canvas_width}x{canvas_height}, 初始缩放={self.scale_factor:.3f}")
            
            # 取消任何待处理的缩放更新
            if self.scale_timer_id:
                self.root.after_cancel(self.scale_timer_id)
                self.scale_timer_id = None
            
            self.update_image_display()
            
            # 创建ROI选择器
            self.roi_selector = ROISelector(self.canvas, self.original_image, self.update_roi_status)
            self.roi_selector.set_canvas_offset(self.canvas_offset_x, self.canvas_offset_y)
            self.update_roi_status() # 加载图像时也更新状态
            
        except Exception as e:
            messagebox.showerror("错误", f"无法加载图像: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def clear_roi(self):
        if self.roi_selector:
            self.roi_selector.clear_roi()
            self.update_roi_status()
    
    def confirm_roi(self):
        if self.roi_selector and self.roi_selector.get_roi_coords():
            coords = self.roi_selector.get_roi_coords()
            messagebox.showinfo("ROI确认", f"已选择ROI区域: {coords}")
            self.update_roi_status()
        else:
            messagebox.showwarning("警告", "请先选择ROI区域")
    
    def calculate(self):
        # 检查文件是否存在
        if not self.img_path.get():
            messagebox.showerror("错误", "请选择图像文件")
            return
        
        if not os.path.exists(self.img_path.get()):
            messagebox.showerror("错误", "图像文件不存在")
            return
        
        # 检查是否选择了ROI
        if not self.roi_selector or not self.roi_selector.get_roi_coords():
            messagebox.showerror("错误", "请先选择ROI区域作为模板")
            return
        
        try:
            # 读取图像
            img = cv2.imread(self.img_path.get(), cv2.IMREAD_GRAYSCALE)
            
            if img is None:
                messagebox.showerror("错误", "无法读取图像文件")
                return
            
            print(f"原始图像尺寸: {img.shape}")
            print(f"当前缩放比例: {self.scale_factor}")
            print(f"画布偏移量: ({self.canvas_offset_x}, {self.canvas_offset_y})")
            
            # 从ROI提取模板
            roi_coords = self.roi_selector.get_roi_coords()
            x1, y1, x2, y2 = roi_coords
            print(f"画布ROI坐标: ({x1}, {y1}, {x2}, {y2})")
            
            # 将画布坐标转换为原始图像坐标
            # 注意：这里需要正确处理坐标转换
            # 画布坐标 -> 缩放后的图像坐标 -> 原始图像坐标
            scaled_x1 = x1 - self.canvas_offset_x
            scaled_y1 = y1 - self.canvas_offset_y
            scaled_x2 = x2 - self.canvas_offset_x
            scaled_y2 = y2 - self.canvas_offset_y
            
            # 转换为原始图像坐标
            original_x1 = int(scaled_x1 / self.scale_factor)
            original_y1 = int(scaled_y1 / self.scale_factor)
            original_x2 = int(scaled_x2 / self.scale_factor)
            original_y2 = int(scaled_y2 / self.scale_factor)
            
            print(f"缩放后坐标: ({scaled_x1:.2f}, {scaled_y1:.2f}, {scaled_x2:.2f}, {scaled_y2:.2f})")
            print(f"转换后的原始坐标: ({original_x1}, {original_y1}, {original_x2}, {original_y2})")
            
            # 确保坐标在图像范围内
            original_x1 = max(0, min(original_x1, img.shape[1]-1))
            original_y1 = max(0, min(original_y1, img.shape[0]-1))
            original_x2 = max(0, min(original_x2, img.shape[1]-1))
            original_y2 = max(0, min(original_y2, img.shape[0]-1))
            
            print(f"边界检查后的坐标: ({original_x1}, {original_y1}, {original_x2}, {original_y2})")
            
            # 确保ROI区域有效（至少1x1像素）
            if original_x2 <= original_x1 or original_y2 <= original_y1:
                messagebox.showerror("错误", f"ROI区域太小，请重新选择。当前区域: ({original_x1},{original_y1},{original_x2},{original_y2})")
                return
            
            # 提取模板
            temp = img[original_y1:original_y2, original_x1:original_x2]
            
            print(f"提取的模板尺寸: {temp.shape}")
            print(f"模板数据类型: {type(temp)}")
            print(f"模板大小: {temp.size}")
            
            if temp.size == 0:
                messagebox.showerror("错误", f"ROI区域无效，模板大小为0。请检查ROI选择。")
                return
            
            print(f"ROI坐标转换: 画布({x1},{y1},{x2},{y2}) -> 原始图像({original_x1},{original_y1},{original_x2},{original_y2})")
            print(f"模板尺寸: {temp.shape}")
            
            # 验证模板是否合理
            if temp.shape[0] < 5 or temp.shape[1] < 5:
                messagebox.showwarning("警告", f"模板尺寸较小 ({temp.shape})，可能影响匹配精度")
            
            # 创建计算器实例并执行计算
            calculator = Get_distort_coefficient(
                gary_image=img,
                template=temp,
                check_size_designed=self.check_size.get(),
                pixel_size=self.pixel_size.get(),
                threshold=self.threshold.get(),
                iou_threshold=self.iou_threshold.get()
            )
            
            # 执行计算
            dev_pred, dev_true, distorted_coeffi, df, result_image, fitting_image = calculator.work()
            
            # 显示结果
            self.display_results(dev_pred, dev_true, distorted_coeffi, df, result_image, fitting_image)
            
            # 显示成功消息
            messagebox.showinfo("成功", "计算完成！结果已保存到文件。")
            
            # 简单确认文件保存
            print("计算完成！结果文件已保存:")
            print("- results.jpg (匹配结果图像)")
            print("- fitting_curve.jpg (畸变曲线图)")
            
        except Exception as e:
            messagebox.showerror("错误", f"计算过程中出现错误: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def display_results(self, dev_pred, dev_true, distorted_coeffi, df, result_image, fitting_image):
        # 清空结果文本区域
        self.result_text.delete(1.0, tk.END)
        
        # 显示畸变系数
        result_text = f"畸变系数计算结果:\n\n"
        result_text += f"三次项系数 a (畸变系数): {distorted_coeffi[0]}\n"
        result_text += f"二次项系数 b (固定偏置): {distorted_coeffi[1]}\n"
        result_text += f"一次项系数 c (容差): {distorted_coeffi[2]}\n\n"
        
        # 判断畸变类型
        if distorted_coeffi[0] > 0:
            result_text += "畸变类型: 桶形畸变 (Barrel Distortion)\n"
        else:
            result_text += "畸变类型: 枕形畸变 (Pincushion Distortion)\n"
        
        result_text += f"\n拟合数据点数: {len(dev_pred)}\n"
        result_text += f"ROI区域: {self.roi_selector.get_roi_coords()}\n\n"
        
        # 显示拟合结果数据
        result_text += "拟合结果数据:\n"
        result_text += f"相机位置 (posi_camera):\n"
        result_text += f"  最小值: {np.min(df['posi_camera']):.2f}\n"
        result_text += f"  最大值: {np.max(df['posi_camera']):.2f}\n\n"

        
        result_text += f"理想位置 (posi_ideal):\n"
        result_text += f"  最小值: {np.min(df['posi_ideal']):.2f}\n"
        result_text += f"  最大值: {np.max(df['posi_ideal']):.2f}\n\n"

        
        result_text += f"偏差值 (dev):\n"
        result_text += f"  最小值: {np.min(dev_true):.2f}\n"
        result_text += f"  最大值: {np.max(dev_true):.2f}\n\n"

        
        result_text += f"结果已保存到:\n"
        result_text += f"- results.jpg (匹配结果图像)\n"
        result_text += f"- fitting_curve.jpg (畸变曲线图)\n"
        
        self.result_text.insert(1.0, result_text)
        
        # 不再需要更新结果预览，用户可以通过按钮查看
        print("计算完成！用户可以通过右侧按钮查看结果文件。")
    
    def update_result_previews(self):
        """更新结果预览图像"""
        try:
            # 清空画布
            self.results_canvas.delete("all")
            self.fitting_canvas.delete("all")
            
            # 显示"计算中..."状态
            self.results_canvas.create_text(140, 100, text="计算完成，结果已保存", fill="green", font=("Arial", 10))
            self.fitting_canvas.create_text(140, 100, text="计算完成，结果已保存", fill="green", font=("Arial", 10))
                
        except Exception as e:
            print(f"更新结果预览时出错: {str(e)}")
    
    def display_result_previews(self, result_image, fitting_image):
        """在画布上直接显示结果图像"""
        try:
            print("开始显示结果预览...")
            # 显示匹配结果图像
            self.display_canvas_image(result_image, self.canvas, "匹配结果")
            
            # 显示畸变曲线图像
            self.display_canvas_image(fitting_image, self.canvas, "畸变曲线")
            print("结果预览显示完成")
                
        except Exception as e:
            print(f"显示结果预览时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def display_canvas_image(self, image, canvas, title):
        """在指定画布上显示图像"""
        try:
            print(f"显示图像 {title}: 类型={type(image)}, 形状={getattr(image, 'shape', 'N/A') if hasattr(image, 'shape') else 'N/A'}")
            
            # 获取画布尺寸
            canvas_width = 600
            canvas_height = 500
            
            # 如果是OpenCV图像，转换为PIL图像
            if isinstance(image, np.ndarray):
                print(f"OpenCV图像: shape={image.shape}")
                if len(image.shape) == 3:
                    # BGR转RGB
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                else:
                    # 灰度图转RGB
                    image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                image = Image.fromarray(image_rgb)
                print(f"转换为PIL图像: size={image.size}")
            
            # 检查图像尺寸
            if not hasattr(image, 'size') or image.size[0] <= 0 or image.size[1] <= 0:
                print(f"图像尺寸无效: {getattr(image, 'size', 'N/A')}")
                self.clear_canvas(canvas, f"图像尺寸无效")
                return
            
            # 计算缩放比例，保持宽高比
            img_width, img_height = image.size
            print(f"图像尺寸: {img_width} x {img_height}")
            
            # 确保缩放后的尺寸至少为1像素
            scale_x = max(1.0, canvas_width / img_width)
            scale_y = max(1.0, canvas_height / img_height)
            scale = min(scale_x, scale_y)
            
            new_width = max(1, int(img_width * scale))
            new_height = max(1, int(img_height * scale))
            print(f"缩放后尺寸: {new_width} x {new_height}")
            
            # 调整图像大小
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # 清除画布并显示新图像
            canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            canvas.create_image(x, y, anchor=tk.NW, image=photo)
            canvas.image = photo  # 保持引用
            
            print(f"成功显示图像 {title}")
            
        except Exception as e:
            self.clear_canvas(canvas, f"无法显示 {title}")
            print(f"显示图像时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def display_result_image(self, image_path, canvas, title):
        """在指定画布上显示结果图像"""
        try:
            # 读取图像
            image = Image.open(image_path)
            
            # 获取画布尺寸
            canvas_width = 600
            canvas_height = 500
            
            # 计算缩放比例，保持宽高比
            img_width, img_height = image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 调整图像大小
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # 清除画布并显示新图像
            canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            canvas.create_image(x, y, anchor=tk.NW, image=photo)
            canvas.image = photo  # 保持引用
            
        except Exception as e:
            self.clear_canvas(canvas, f"无法加载 {title}")
            print(f"显示图像 {image_path} 时出错: {str(e)}")
    
    def clear_canvas(self, canvas, message):
        """清空画布并显示消息"""
        canvas.delete("all")
        canvas.create_text(140, 100, text=message, fill="gray", font=("Arial", 10))
    
    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
        if self.roi_selector:
            self.roi_selector.clear_roi()
            self.update_roi_status() # 清空结果时也更新状态
        
        # 不再需要清空结果预览
        print("结果已清空")

    def open_result_file(self, filename):
        """打开保存的计算结果文件"""
        try:
            # 检查文件是否存在
            if os.path.exists(filename):
                print(f"正在打开文件: {filename}")
                
                # 获取文件信息
                file_size = os.path.getsize(filename)
                file_time = os.path.getmtime(filename)
                print(f"文件大小: {file_size} 字节, 修改时间: {file_time}")
                
                # 使用系统默认程序打开文件
                if os.name == 'nt':  # Windows
                    os.startfile(filename)
                elif os.name == 'posix':  # macOS 和 Linux
                    import subprocess
                    subprocess.run(['open', filename])  # macOS
                else:
                    import subprocess
                    subprocess.run(['xdg-open', filename])  # Linux
                
                print(f"文件 {filename} 已打开")
            else:
                messagebox.showwarning("警告", f"文件 '{filename}' 不存在。请先计算结果。")
                print(f"文件不存在: {filename}")
                
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件 {filename}: {str(e)}")
            print(f"打开文件时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def check_result_files(self):
        """检查结果文件是否存在和最新"""
        files_status = {}
        
        for filename in ['results.jpg', 'fitting_curve.jpg']:
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                file_time = os.path.getmtime(filename)
                files_status[filename] = {
                    'exists': True,
                    'size': file_size,
                    'time': file_time
                }
                print(f"文件 {filename}: 存在, 大小: {file_size} 字节, 修改时间: {file_time}")
            else:
                files_status[filename] = {
                    'exists': False,
                    'size': 0,
                    'time': 0
                }
                print(f"文件 {filename}: 不存在")
        
        return files_status

def main():
    root = tk.Tk()
    app = DistortionCoefficientGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

    