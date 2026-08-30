#!/usr/bin/env Rscript
# 测试yuima包的基本功能：SDE模型定义、模拟、参数估计

cat("=" , rep("=", 59), "\n", sep="")
cat("yuima包基本功能测试\n")
cat("=" , rep("=", 59), "\n", sep="")

library(yuima)

# 测试1：几何布朗运动模型定义和模拟
cat("\n【测试1】几何布朗运动模型定义和模拟\n")
gbm_model <- setYuima(
  model = setModel(drift = "mu*x", diffusion = "sigma*x", state.variable = "x", time.variable = "t")
)
cat("模型定义成功\n")
cat("漂移项: mu*x\n")
cat("扩散项: sigma*x\n")

# 模拟GBM路径（用setSampling创建采样方案）
set.seed(42)
samp <- setSampling(Terminal = 1, n = 252)
gbm_sim <- simulate(gbm_model, true.parameter = list(mu = 0.05, sigma = 0.2), 
                    xinit = 100, sampling = samp)
cat("模拟成功，路径长度:", length(gbm_sim@data@original.data), "\n")
cat("初始值:", gbm_sim@data@original.data[1], "\n")
cat("终值:", gbm_sim@data@original.data[length(gbm_sim@data@original.data)], "\n")

# 测试2：GBM参数估计（qmle）
cat("\n【测试2】GBM参数估计（qmle）\n")
# 用模拟数据进行参数估计
gbm_qmle <- qmle(gbm_sim, start = list(mu = 0.01, sigma = 0.1), 
                  lower = list(mu = -1, sigma = 0.01),
                  upper = list(mu = 1, sigma = 1))
cat("参数估计成功\n")
cat("估计的mu:", coef(gbm_qmle)["mu"], "\n")
cat("估计的sigma:", coef(gbm_qmle)["sigma"], "\n")
cat("真实mu: 0.05, 真实sigma: 0.2\n")
cat("AIC:", AIC(gbm_qmle), "\n")
cat("BIC:", BIC(gbm_qmle), "\n")

# 测试3：跳跃扩散模型定义
cat("\n【测试3】跳跃扩散模型定义\n")
# 定义跳跃扩散模型：dX = mu*X*dt + sigma*X*dW + X*dN
# 其中N是泊松过程，跳跃幅度服从正态分布
jd_model <- setYuima(
  model = setModel(
    drift = "mu*x", 
    diffusion = "sigma*x", 
    state.variable = "x", 
    time.variable = "t",
    jump.coeff = "x",
    measure = list(df = "dn", measure.type = "CP"),
    parameter = list(mu = 0.05, sigma = 0.2, lambda = 1, xi = 0, rho = 0.1)
  )
)
cat("跳跃扩散模型定义成功\n")
cat("漂移项: mu*x\n")
cat("扩散项: sigma*x\n")
cat("跳跃系数: x\n")
cat("跳跃强度: lambda\n")
cat("跳跃幅度均值: xi\n")
cat("跳跃幅度标准差: rho\n")

# 模拟跳跃扩散路径（用setSampling创建采样方案）
set.seed(42)
samp2 <- setSampling(Terminal = 1, n = 252)
jd_sim <- simulate(jd_model, true.parameter = list(mu = 0.05, sigma = 0.2, lambda = 2, xi = -0.1, rho = 0.15), 
                   xinit = 100, sampling = samp2)
cat("跳跃扩散模拟成功，路径长度:", length(jd_sim@data@original.data), "\n")
cat("初始值:", jd_sim@data@original.data[1], "\n")
cat("终值:", jd_sim@data@original.data[length(jd_sim@data@original.data)], "\n")

# 计算收益率
returns <- diff(log(jd_sim@data@original.data))
cat("收益率数量:", length(returns), "\n")
cat("平均收益率:", mean(returns), "\n")
cat("收益率标准差:", sd(returns), "\n")
cat("最小收益率:", min(returns), "\n")
cat("最大收益率:", max(returns), "\n")

# 测试4：输出JSON格式的参数估计结果
cat("\n【测试4】输出JSON格式的参数估计结果\n")
result <- list(
  model = "GBM",
  parameters = list(
    mu = as.numeric(coef(gbm_qmle)["mu"]),
    sigma = as.numeric(coef(gbm_qmle)["sigma"])
  ),
  aic = as.numeric(AIC(gbm_qmle)),
  bic = as.numeric(BIC(gbm_qmle)),
  log_likelihood = as.numeric(logLik(gbm_qmle))
)

# 用基础R输出JSON（避免依赖jsonlite）
cat("{\n")
cat('  "model": "GBM",\n')
cat('  "parameters": {\n')
cat('    "mu": ', result$parameters$mu, ',\n', sep="")
cat('    "sigma": ', result$parameters$sigma, '\n', sep="")
cat('  },\n')
cat('  "aic": ', result$aic, ',\n', sep="")
cat('  "bic": ', result$bic, ',\n', sep="")
cat('  "log_likelihood": ', result$log_likelihood, '\n', sep="")
cat("}\n")

cat("\n" , rep("=", 60), "\n", sep="")
cat("测试完成\n")
cat(rep("=", 60), "\n", sep="")
