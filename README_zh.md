# 镓基液态金属合金热导率预测

本仓库提供**镓基液态金属热导率可解释机器学习研究**的配套预测实现，采用最终SISSO解析组成模型，以及Ga–In和Ga–In–Sn的条件温度扩展。使用者可以计算单个配方，或批量处理组成表，进行高通量组成探索。Ga–Sn采用298 K组成模型。

[English](README.md)

## 环境与模型配置

### 本地准备

下载仓库ZIP并解压，在解压文件夹内打开终端。预测工具需要**Python3.10及以上版本**，使用标准库。检查安装并查看参数：

```bash
python --version
python predict.py --help
```

若系统使用`python3`，相应替换命令。可选用Conda建立隔离环境：

```bash
conda create -n ga-lm-predict python=3.11
conda activate ga-lm-predict
```

### 建模环境

SISSO数值复现和配置比较采用下表记录环境。建模软件与预测工具的运行依赖分别列示。

| 软件 | 版本／设置 |
|---|---|
| Python／TorchSisso | 3.11.15／0.1.8 |
| PyTorch | 2.14.1；CPU；配置比较：单线程、种子20261005 |
| NumPy／pandas | 2.4.6／3.0.6 |
| scikit-learn／SciPy／SymPy | 1.9.1／1.17.1／1.14.0 |

### 核心建模配置

| 环节 | 配置 |
|---|---|
| 数据与特征 | 298 K的44个组成；Ga质量含量75、80、85、90 wt%，每系列11条。初始输入：10项手工组成／属性特征与132项Magpie统计量 |
| 折内预处理 | 训练折中位数填补；剔除方差≤10⁻⁵的列及绝对Pearson相关系数>0.95的后列；采用训练均值和总体标准差标准化 |
| 参照SISSO搜索 | 算子`+`、`-`、`*`、`/`、`pow(2)`；实际扩展1层（`no_of_operators=2`）；`sis_features=6`；两描述符加截距，取自后端上限`dimension=3` |
| 配置比较 | 两／三组成坐标路线扩展1–2层；参照、属性派生及联合路线扩展1层。预算10／20，另对三坐标2层及联合1层考察40；1–3描述符，共48个配置 |
| 评价 | 44折留一与四个Ga系列留出；各折重新预处理、搜索和拟合，从汇总留出预测计算RMSE、MAE、R² |
| 最终模型 | 仅训练集的描述符最小二乘拟合；选定方程用全部44条记录拟合，反标准化至原子分数，并利用组成闭合关系化简 |

参照过滤保留三个原子分数、熔点标准差、最大原子序数及最大共价半径。属性派生及联合比较路线进行方差过滤和标准化，同时保留相关输入。扩展候选检查数值有限性与非零变异。

固定RF／ANN／GPR重放采用Python3.14.4、scikit-learn1.8.0和随机种子17，输入为上述六项参照特征。RF：500棵树、不限最大深度、最小叶样本数1；ANN：隐层(16,8)、ReLU／Adam、alpha0.02、学习率0.005、迭代上限5000；GPR：Constant×RBF+WhiteKernel、alpha10⁻⁸、目标归一化、优化重启5次。GPR和ANN在训练折内标准化。完整特征定义与搜索／评价设置见论文Methods和补充方法S1–S3。

## 使用预测脚本

1. **指定组成与温度。** Ga、In、Sn输入为合计100的百分数。默认质量百分比和298 K；未添加的组元为0。
2. **运行预测。** 以质量组成Ga75In25为例：

```bash
python predict.py --ga 75 --in 25
```

3. **查看结果。** 命令输出一条CSV记录，该例的主要字段如下：

| 字段 | 数值 |
|---|---:|
| `T_K` | 298 |
| `x_Ga`／`x_In` | 0.83165893／0.16834107 |
| `k_W_mK` | 26.96843819 |

`x_Ga`、`x_In`、`x_Sn`为原子分数，`k_W_mK`为热导率，单位W m⁻¹ K⁻¹。原子百分比输入使用`--basis at-percent`：

```bash
python predict.py --ga 85.8 --in 14.2 --basis at-percent
```

条件温度估算：

```bash
python predict.py --ga 75 --in 25 --temperature 350 --engineering-temperature
```

该例得到**29.82843819 W m⁻¹ K⁻¹**，输出同时注明温度模式。温度单位为K。Python中也可先`from predict import predict`，再调用`predict(75, 25, 0)`。

## 批量与高通量预测

准备包含`Ga,In,Sn`的CSV；可选`sample_id`和`T_K`用于标识样本并指定各行温度：

```csv
sample_id,Ga,In,Sn,T_K
binary,75,25,0,298
ternary,75,15,10,298
```

保存为`compositions.csv`，执行：

```bash
python predict.py --input compositions.csv --output predictions.csv
```

输出保留原行序和标识，主要结果为：

| `sample_id` | `k_W_mK` |
|---|---:|
| binary | 26.96843819 |
| ternary | 24.73589925 |

每行还包含原子分数、`k_298_W_mK`、实际斜率`b_W_mK2`、温度模式及计算状态。无效行注明原因，其他行继续；覆盖已有输出需`--overwrite`。同一文件的组成基准通过`--basis`选择；温度空值采用`--temperature`，默认为298 K。温度修正批次添加`--engineering-temperature`。

脚本逐行处理大规模组成表。可先生成质量百分比网格，再计算：

```bash
python examples/make_scan.py --ga-min 75 --ga-max 90 --step 0.5 --output scan.csv
python predict.py --input scan.csv --output predictions_scan.csv
```

## 解析模型与适用条件

参考温度方程为：

$$
k_{298}=338.24x_{\mathrm{Ga}}x_{\mathrm{In}}+17.31x_{\mathrm{Ga}}-206.62x_{\mathrm{In}}+41.12x_{\mathrm{Sn}}.
$$

原子分数合计1。质量转换采用Ga69.723、In114.818、Sn118.710，脚本使用全精度系数计算。

| 体系 | 温度处理 |
|---|---|
| Ga–In | 298 K基值；可选$k(T)=k_{298}+0.055(T-298)$ |
| Ga–In–Sn | 298 K基值；可选$k(T)=k_{298}+0.060(T-298)$ |
| Ga–Sn | 仅298 K |

斜率单位为W m⁻¹ K⁻²，属于由实验系列比较得到的条件工程近似，应在组成对应的液态测量条件内使用。组成扫描用于探索模型响应，选择实际材料时须确认目标温度下的液态资格。拟合样本的Ga质量含量为75–90 wt%，另有来源匹配的外部选择比较；拟合组成以外的估算结合论文组成与温度评价解读。
