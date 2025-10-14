# 畸变系数计算器（GUI）

这是一个用于通过模板匹配方法计算相机畸变系数的图形化工具。程序使用 OpenCV 提取图像中格点（或标记）中心位置，计算实际像素位置与理论（设计）像素位置的偏差，并拟合出一条畸变曲线以及畸变系数（采用三次多项式拟合）。

## 特性

- 基于模板匹配自动检测标记/格点并绘制匹配框
- 支持在 GUI 中通过鼠标拖拽选择 ROI 作为模板
- 可设置标片设计尺寸、像素尺寸、匹配阈值和 IOU 阈值等参数
- 使用 scipy 的 curve_fit 拟合畸变函数（a*(x-b)^3 + c）并输出拟合曲线
- 生成并保存匹配结果图像、拟合曲线图和匹配框位置信息 CSV
- 支持缩放、右键拖动图像预览和缓存缩放结果以提高交互性能

## 依赖

程序使用以下 Python 包（见 `requirements.txt`）：

- opencv-python >= 4.5
- numpy >= 1.20
- pandas >= 1.3
- scipy >= 1.7
- matplotlib >= 3.4
- pillow >= 8.0

建议使用虚拟环境（venv 或 conda）来安装依赖。

## 安装

在项目根目录（包含 `get_distortedCoefficient_gui.py`）下执行：

```powershell
# 创建并激活 venv（Windows PowerShell）
python -m venv .venv; .\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

如果你使用的是 cmd 或者其他 shell，请相应调整激活命令。

## 运行

在激活的虚拟环境中运行：

```powershell
python get_distortedCoefficient_gui.py
```

程序将弹出一个 GUI 窗口。

## 使用说明（GUI）

1. 文件选择：点击“浏览”选择要计算的图像文件（支持 BMP/JPG/PNG/TIF 等）。
2. ROI 选择：在右侧图像预览区域，左键拖拽选择一个区域作为模板（标记的单元）。
   - 你可以通过鼠标滚轮缩放图像；右键拖动用于平移图像。
   - 点击“确认ROI”可确认所选区域，点击“清除ROI”移除选择。
3. 参数设置：
   - 标片设计尺寸 (μm)：标片上相邻标记的设计间距（示例值：40）。
   - 像素尺寸 (μm/pix)：相机像素对应的物理尺寸（示例值：0.714268）。
   - 匹配阈值 (threshold)：模板匹配的置信度阈值（0.0-1.0）。
   - IOU 阈值 (iou_threshold)：用于过滤重叠检测结果的阈值（0.0-1.0）。
4. 开始计算：点击“开始计算”按钮。程序会：
   - 从所选 ROI 提取模板并在整图中批量匹配。
   - 绘制匹配框和中心点并保存为 `results.jpg`。
   - 计算以图像中心为零点的相机像素位置 (`posi_camera`) 和理论像素位置 (`posi_ideal`)。
   - 使用三次多项式拟合偏差并保存拟合曲线为 `fitting_curve.jpg`。
   - 将匹配框位置信息保存为 `matching_boxes.csv`。
5. 查看结果：计算完成后，可通过 GUI 中的按钮直接打开 `results.jpg`、`fitting_curve.jpg` 或 `matching_boxes.csv`。

## 输出文件说明

- `results.jpg`：匹配结果图像，图中包含检测到的匹配框与中心点（用于人工检查匹配质量）。
- `fitting_curve.jpg`：畸变拟合曲线图（包含拟合曲线与实际测量点）。
- `matching_boxes.csv`：CSV 文件，包含每个匹配框的位置信息（x, y, width, height, center_x, center_y, area）以及索引。

## 编程细节（快速阅读）

- 主程序文件：`get_distortedCoefficient_gui.py`。
- 模板匹配实现：`tempMatcher.py`（程序通过 `TemplateMatcher` 类进行匹配，匹配结果返回矩形框和数据表）。
- 畸变模型：dev(x) = a*(x - b)^3 + c，使用 `scipy.optimize.curve_fit` 拟合 a、b、c。
- GUI：基于 `tkinter`，使用 `PIL.Image` / `ImageTk` 做图像显示与缩放缓存优化。

## 调优建议与常见问题

- 匹配阈值过高：可能会导致漏检（匹配数太少），过低则可能误检。建议先用默认值（0.9）尝试，再根据结果调整。
- 模板尺寸：建议选择包含完整标记的区域，且尺寸不要过小（至少 5x5 像素）。
- ROI 坐标转换：GUI 中的 ROI 坐标将被按当前缩放比例和偏移量转换回原始图像坐标；若出现位置偏差，请检查缩放/拖动是否在选择时完成。
- 如果 `cv2.imread` 无法读取图像（返回 None），请确认文件路径没有中文或特殊字符，或尝试使用不同格式的图片。
- 当程序报错时，可查看控制台输出的 traceback（GUI 会弹出错误对话框并在控制台打印详细信息）。

## 打包（可选）

仓库中已包含 `build/` 目录，若想重新打包为独立可执行文件，可使用 PyInstaller：

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed get_distortedCoefficient_gui.py
```

请根据实际需要调整 PyInstaller 的参数。

## 许可证与联系方式

本仓库未注明具体许可证。若需要在工程中使用或发布，请自行补充许可证信息（例如 MIT）。

如需帮助或发现 bug，请在项目中打开 issue，或直接联系维护者（在项目中添加联系方式）。

---

感谢使用本工具，如果你希望 README 增加示例截图、快速演示视频或更详细的打包说明，我可以继续补充。