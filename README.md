# Thermal conductivity prediction for Ga-based liquid-metal alloys

This repository provides the prediction implementation accompanying our study of **thermal conductivity in Ga-based liquid-metal alloys using interpretable machine learning**. It implements the final SISSO analytical composition model and its conditional temperature extension for Ga–In and Ga–In–Sn. Researchers can calculate individual compositions or process large composition tables for high-throughput exploration. Ga–Sn predictions use the 298 K composition model.

[中文说明](README_zh.md)

## Environment and model configuration

### Local setup

Download the repository ZIP, extract it, and open a terminal in the extracted folder. The predictor requires **Python 3.10 or later** and uses the standard library. Check your installation with:

```bash
python --version
python predict.py --help
```

Use `python3` if that is your system's Python command. For an optional isolated environment:

```bash
conda create -n ga-lm-predict python=3.11
conda activate ga-lm-predict
```

### Modeling environment

The SISSO numerical reproduction and configuration comparison used the recorded environment below. These modeling packages are separate from the predictor's runtime requirements.

| Component | Version / setting |
|---|---|
| Python / TorchSisso | 3.11.15 / 0.1.8 |
| PyTorch | 2.14.1; CPU; configuration comparison: one thread, seed 20261005 |
| NumPy / pandas | 2.4.6 / 3.0.6 |
| scikit-learn / SciPy / SymPy | 1.9.1 / 1.17.1 / 1.14.0 |

### Core modeling settings

| Stage | Configuration |
|---|---|
| Data and features | 44 compositions at 298 K; Ga = 75, 80, 85 and 90 wt%, 11 records per series. Initial inputs: 10 manually defined composition/property features and 132 Magpie statistics |
| Fold preprocessing | Training-fold median imputation; remove variance ≤10⁻⁵ and later columns with absolute Pearson correlation >0.95; standardize using training mean and population standard deviation |
| Reference SISSO search | Operators `+`, `-`, `*`, `/`, `pow(2)`; one actual expansion layer (`no_of_operators=2`); `sis_features=6`; two descriptors plus intercept, from backend limit `dimension=3` |
| Configuration comparison | Two-/three-coordinate composition routes: 1–2 layers; reference, property-derived and combined routes: 1 layer. Budgets 10/20, with additional 40 checks for three-coordinate depth 2 and combined depth 1; 1–3 descriptors, yielding 48 configurations |
| Evaluation | 44-fold leave-one-out and four Ga-series holdouts; preprocessing, search and fitting repeated within each fold; pooled RMSE, MAE and R² |
| Final model | Training-only least-squares descriptor fitting; selected equation fitted to all 44 records, transformed back to atomic fractions and simplified using composition closure |

The reference filtering retains the three atomic fractions, melting-temperature deviation, maximum atomic number and maximum covalent radius. The property-derived and combined comparison routes apply variance filtering and scaling while retaining correlated inputs. Expanded candidates are checked for finite values and nonzero variation.

The fixed RF/ANN/GPR replay used Python 3.14.4, scikit-learn 1.8.0 and random state 17 with the six reference inputs. RF uses 500 trees, unrestricted depth and minimum leaf size 1; ANN uses layers (16,8), ReLU/Adam, alpha 0.02, learning rate 0.005 and 5000 iterations; GPR uses Constant×RBF+WhiteKernel, alpha 10⁻⁸, target normalization and five optimizer restarts. GPR and ANN standardize within each training fold. Full feature definitions and search/evaluation settings are described in the study's Methods and Supplementary Methods S1–S3.

## How to use the prediction script

1. **Specify composition and temperature.** Enter Ga, In and Sn as percentages summing to 100. The default basis is mass percent and the default temperature is 298 K. An absent component is zero.
2. **Run the prediction.** For Ga75In25 by mass:

```bash
python predict.py --ga 75 --in 25
```

3. **Read the result.** The command prints one CSV record. Selected output fields for this example are:

| Field | Value |
|---|---:|
| `T_K` | 298 |
| `x_Ga` / `x_In` | 0.83165893 / 0.16834107 |
| `k_W_mK` | 26.96843819 |

`x_Ga`, `x_In` and `x_Sn` are atomic fractions; `k_W_mK` is thermal conductivity in W m⁻¹ K⁻¹. For atomic-percent input, use `--basis at-percent`:

```bash
python predict.py --ga 85.8 --in 14.2 --basis at-percent
```

For a conditional temperature estimate:

```bash
python predict.py --ga 75 --in 25 --temperature 350 --engineering-temperature
```

This gives **29.82843819 W m⁻¹ K⁻¹**, with the temperature mode reported in the output. Temperatures are in kelvin. Python users can also call `predict(75, 25, 0)` after `from predict import predict`.

## Batch and high-throughput prediction

Prepare a CSV containing `Ga,In,Sn`; optional `sample_id` and `T_K` columns identify samples and specify row temperatures:

```csv
sample_id,Ga,In,Sn,T_K
binary,75,25,0,298
ternary,75,15,10,298
```

Save it as `compositions.csv`, then run:

```bash
python predict.py --input compositions.csv --output predictions.csv
```

The output retains row order and identifiers. Selected results are:

| `sample_id` | `k_W_mK` |
|---|---:|
| binary | 26.96843819 |
| ternary | 24.73589925 |

Each row also reports atomic fractions, `k_298_W_mK`, the applied slope `b_W_mK2`, temperature mode and calculation status. Invalid rows receive an explanation while other rows continue. Existing output files require `--overwrite`. The file uses one composition basis, selected with `--basis`; blank temperatures use `--temperature`, defaulting to 298 K. Add `--engineering-temperature` for temperature-corrected batches.

The script processes rows sequentially for large tables. To generate a mass-percent composition grid and calculate it:

```bash
python examples/make_scan.py --ga-min 75 --ga-max 90 --step 0.5 --output scan.csv
python predict.py --input scan.csv --output predictions_scan.csv
```

## Analytical model and applicable conditions

The reference-temperature equation is

$$
k_{298}=338.24x_{\mathrm{Ga}}x_{\mathrm{In}}+17.31x_{\mathrm{Ga}}-206.62x_{\mathrm{In}}+41.12x_{\mathrm{Sn}},
$$

where atomic fractions sum to one. The script converts mass percentages using Ga = 69.723, In = 114.818 and Sn = 118.710, and evaluates full-precision coefficients.

| System | Temperature treatment |
|---|---|
| Ga–In | 298 K baseline; optional $k(T)=k_{298}+0.055(T-298)$ |
| Ga–In–Sn | 298 K baseline; optional $k(T)=k_{298}+0.060(T-298)$ |
| Ga–Sn | 298 K only |

The slopes, in W m⁻¹ K⁻², are conditional engineering approximations from the experimental-series comparison. Apply them within composition-appropriate liquid-state measurement conditions. Composition scans support exploration of the model response; confirm liquid state at the target temperature when selecting alloys. The fitting samples span 75–90 wt% Ga, with additional source-matched external selection comparisons reported in the study. Use the paper's composition and temperature assessments when interpreting estimates beyond the fitting compositions.
