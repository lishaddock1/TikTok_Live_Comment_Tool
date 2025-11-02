@echo off
chcp 65001 > nul  # 解决中文乱码
cls

:: 配置项
set "PROJECT_DIR=E:\_project"  # 项目根目录
set "VENV_NAME=.env"            # 虚拟环境目录
set "MITMPROXY_PORT=8080"       # mitmproxy端口
set "PYTHON_SCRIPT=main.py"     # 主程序文件名
set "MITM_HANDLER=mitmproxy_handler.py"  # 拦截脚本名

:: 切换到项目目录
echo [1/4] 正在切换到项目目录：%PROJECT_DIR%
cd /d %PROJECT_DIR%
if %errorlevel% neq 0 (
    echo 错误：项目目录不存在！请检查PROJECT_DIR配置。
    pause
    exit /b 1
)

:: 激活虚拟环境
echo [2/4] 正在激活虚拟环境：%VENV_NAME%
call %VENV_NAME%\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo 错误：虚拟环境激活失败！
    pause
    exit /b 1
)
echo 虚拟环境激活成功！

:: 启动mitmproxy（禁用HTTP/2，使用公共DNS）
echo [3/4] 正在启动mitmproxy（端口：%MITMPROXY_PORT%）...
start cmd /k "echo mitmproxy控制台（关闭此窗口会停止代理）& echo =============================& mitmproxy -s %MITM_HANDLER% -p %MITMPROXY_PORT% --no-http2 --set dns_server=8.8.8.8"
if %errorlevel% neq 0 (
    echo 错误：mitmproxy启动失败！请确认已安装mitmproxy。
    pause
    exit /b 1
)

:: 启动Python服务
echo [4/4] 正在启动TikTok解析服务...
start cmd /k "echo TikTok解析服务控制台& echo =============================& python %PYTHON_SCRIPT%"
if %errorlevel% neq 0 (
    echo 错误：Python服务启动失败！
    pause
    exit /b 1
)

:: 启动完成提示
echo.
echo 所有服务启动完成！请按以下步骤操作：
echo 1. 确保SwitchyOmega已切换到「自动切换（TikTok）」模式
echo 2. 访问TikTok直播页面（如https://www.tiktok.com/@主播名/live）
echo 3. 若出现证书错误，请安装mitmproxy证书（访问http://mitm.it）
echo.
pause
    