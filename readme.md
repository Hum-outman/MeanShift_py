## Mean Shift Clustering
MeanShift_py is a simple implementation of [mean shift](http://en.wikipedia.org/wiki/Mean_shift) clustering in python.

## 房子出售信息监测程序（Windows `.exe`）

新增了一个独立的桌面程序 `house_monitor.py`，用于监测**连江县天福元润国际小区 4 号楼**的公开出售信息。程序会从您填写的公开房源检索页中筛选同时包含“小区名”和“4号楼/4栋”的卡片，记录总价、单价、链接和首次/最后发现时间；发现新房源时会弹窗并响铃。数据保存在当前 Windows 用户目录下的 `.tianfu_yuanrun_monitor/monitor.db`。

> 请仅填写允许自动访问的公开检索页，遵守房源平台的服务条款；本程序不会绕过登录、验证码或反爬限制。不同网站页面结构不同，建议先点击“立即检查”确认结果。

### 直接运行

```bash
python house_monitor.py
```

程序已预填“天福元润国际”的安居客小区结果页；双击 EXE 后可直接点击“立即检查”。“打开网页”按钮会在默认浏览器中打开该链接，方便人工确认房源。设置检查间隔（最少 5 分钟）后，点击“开始监测”。如果网站改版或拒绝自动访问，可将输入框中的链接替换为其他允许公开自动访问的搜索结果页。

### 生成 Windows EXE

在 Windows 的命令提示符中运行：

```bat
build_exe.bat
```

构建完成后可将 `dist\TianFuYuanRunMonitor.exe` 复制到 Windows 电脑运行；首次运行不需要安装 Python。构建阶段需要网络下载 PyInstaller。

### 获取已构建的 EXE

本仓库包含 Windows GitHub Actions 构建工作流 `.github/workflows/build-windows-exe.yml`。推送代码后，在 GitHub 的 **Actions → Build Windows EXE → Run workflow** 手动运行；完成后从该次运行页面的 **Artifacts** 下载 `TianFuYuanRunMonitor-windows`，解压即可得到 `TianFuYuanRunMonitor.exe`。该工作流使用 Windows 环境构建，生成的文件才是可在 Windows 上运行的真正 `.exe`。


<table>
<tr>
<td><img src="sample_images/ms_2d_bw_2.gif"/></td>
<td><img src="sample_images/ms_2d_bw_.8.gif"/></td>
</tr>
</table>

### Dependencies
The only dependency is [Numpy](http://www.numpy.org/)

### Description
The `mean_shift.py` module defines a class called `MeanShift`. The `MeanShift` class constructor takes in an optional kernel parameter. If no kernel is specified, a default [Gaussian](http://en.wikipedia.org/wiki/Gaussian_function) kernel is used.

The `cluster` method requires an array of points and a kernel bandwidth value. A optional `iteration_callback` function can also be passed in that will be called back at the end of each mean shift iteration with the current state of the algorithm (e.g., where the points are currently at, along with an iteration number).

After the clustering finishes, a `MeanShiftResult` object is returned, containing three arrays:

1. The original points
2. The shifted points
3. Cluster assignments for each point

### Usage
```python
import mean_shift as ms

data = get_data_from_somewhere()
mean_shifter = ms.MeanShift()
mean_shift_result = mean_shifter.cluster(data, kernel_bandwidth = 10)

original_points =  mean_shift_result.original_points
shifted_points = mean_shift_result.shifted_points
cluster_assignments = mean_shift_result.cluster_ids

# If you want to use multivariate gaussian kernel
# By default it uses unviariate gaussian kernel
# Make sure the dimensions of 'data' and the kernel match
mean_shifter = ms.MeanShift(kernel='multivariate_gaussian')
mean_shift_result = mean_shifter.cluster(data, kernel_bandwidth = [10,20,30])
```

### Example
#### Plotting Into Graph
This is example using matplotlib to plot graphs
```python
import mean_shift as ms
import matplotlib.pyplot as plt
import numpy as np

data = np.genfromtxt('data.csv', delimiter=',')

mean_shifter = ms.MeanShift()
mean_shift_result = mean_shifter.cluster(data, kernel_bandwidth = 1)

original_points =  mean_shift_result.original_points
shifted_points = mean_shift_result.shifted_points
cluster_assignments = mean_shift_result.cluster_ids

x = original_points[:,0]
y = original_points[:,1]
Cluster = cluster_assignments
centers = shifted_points

fig = plt.figure()
ax = fig.add_subplot(111)
scatter = ax.scatter(x,y,c=Cluster,s=50)
for i,j in centers:
    ax.scatter(i,j,s=50,c='red',marker='+')
ax.set_xlabel('x')
ax.set_ylabel('y')
plt.colorbar(scatter)

fig.savefig("mean_shift_result")
```

<img width=400 src="sample_images/mean_shift_result.png"/>

#### Image Segmentation
Mean shift can be used for image segmentation. Below is an example of an image being mean shift clustered in 3D RGB space, resulting in 7 clusters.

<img width=400 src="sample_images/ms_3d_image_animation.gif"/>

<table border="0">
<tr>
<td><img src="sample_images/mean_shift_image.jpg"/></td>
<td><img src="sample_images/mean_shift_image_clustered.png"/></td>
</tr>
</table>
