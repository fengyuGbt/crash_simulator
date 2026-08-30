# 用 yuima 拟合股价随机微分方程（SDE），估计漂移/波动参数
#
# 模型（对数价格布朗运动）：
#   dX = mu*dt + sigma*dW ，X = log(price)
#   - mu     日度对数漂移（趋势）
#   - sigma  日度波动率
#
# 用法：Rscript fit_sde.R <prices.csv> <out.json>
# CSV 列：date,close
# 输出 JSON：{ticker, n, mu_annual, sigma_annual, rv_annual, ...}
library(yuima)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
csv_path <- args[1]
out_path <- args[2]
ticker <- if (length(args) >= 3) args[3] else sub("_px$", "", sub("\\..*$", "", basename(csv_path)))

px <- read.csv(csv_path, stringsAsFactors = FALSE)
px$date <- as.Date(px$date)
px <- px[order(px$date), ]
px <- px[!is.na(px$close) & px$close > 0, ]
n <- nrow(px)

logx <- log(px$close)
# 已实现波动率（日收益标准差，年化）
daily_ret <- diff(logx)
rv_annual <- sd(daily_ret) * sqrt(252)

# 对数价格的带漂移布朗运动模型
mod <- setModel(drift = "mu", diffusion = "sigma", solve.variable = "x")
y <- setYuima(model = mod, data = setData(logx, delta = 1 / 252))

res <- tryCatch({
    est <- qmle(y, start = list(mu = 0.1, sigma = 0.3), method = "L-BFGS-B",
                lower = c(mu = -5, sigma = 1e-4), upper = c(mu = 5, sigma = 5))
    co <- coef(est)
    se <- tryCatch(sqrt(diag(vcov(est))), error = function(e) c(NA, NA))
    list(mu_d = as.numeric(co["mu"]), sigma_d = as.numeric(co["sigma"]),
         mu_se = as.numeric(se[1]), sigma_se = as.numeric(se[2]),
         ll = as.numeric(logLik(est)))
}, error = function(e) {
    list(mu_d = NA, sigma_d = NA, mu_se = NA, sigma_se = NA, ll = NA)
})

# 说明：delta=1/252（时间单位=年）下，qmle 直接输出年化参数：
#   mu = 年化对数漂移（趋势），sigma = 年化波动率，无需再乘 252/sqrt(252)
out <- list(
    ticker = ticker,
    n = n,
    start_date = as.character(px$date[1]),
    end_date = as.character(px$date[n]),
    last_close = px$close[n],
    mu_annual = res$mu_d,
    sigma_annual = res$sigma_d,
    mu_se_annual = res$mu_se,
    sigma_se_annual = res$sigma_se,
    rv_annual = rv_annual,
    loglik = res$ll
)
write(toJSON(out, auto_unbox = TRUE, digits = 6), out_path)
cat(sprintf("[SDE] %s n=%d mu_annual=%.4f sigma_annual=%.4f rv_annual=%.4f\n",
            out$ticker, n, out$mu_annual, out$sigma_annual, out$rv_annual))
