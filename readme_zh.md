# PLAXIS 3D 桩靴贯入自动化工具

[English README (英文版 README)](readme.md)

PLAXIS 3D 桩靴贯入自动化工具是一款桌面应用程序，旨在简化和自动化使用 PLAXIS 3D 进行桩靴贯入分析的过程。它提供了一个用户友好的图形界面，用于输入参数、控制分析和查看结果，所有这些都基于 "基于PLAXIS3D的海洋桩靴入泥深度设计流程.pdf" 中详述的工作流程。

## 主要功能

*   **项目管理:** 创建、保存和加载分析项目。
*   **直观的数据输入:**
    *   定义桩靴几何形状，并提供可视化反馈。
    *   为多种土体模型（例如，Mohr-Coulomb、Hardening Soil）指定多层土层和材料属性。
    *   输入加载条件和分析控制参数。
    *   配置地下水位深度。
*   **自动化的 PLAXIS 工作流:**
    *   根据用户输入生成 PLAXIS 命令/脚本。
    *   在单独的线程中管理 PLAXIS 分析的执行，以保持用户界面的响应性。
    *   提供实时进度更新和日志。
*   **结果可视化:**
    *   显示最终贯入深度和峰值阻力等关键结果。
    *   使用 Matplotlib 绘制荷载-贯入曲线。
    *   在表格中显示详细结果。
*   **数据导出:** 将图表导出为图像，将表格数据导出为 CSV 文件。
*   **配置:** 设置本地 PLAXIS 安装路径。

## 技术栈

*   **后端逻辑:** Python (开发过程中使用 3.12 版本)
*   **图形用户界面 (GUI):** PySide6 (Python 的 Qt6 绑定)
*   **PLAXIS 交互:**
    *   主要使用 PLAXIS Python 脚本 API。
    *   使用自定义的 `plxscripting` 库 (版本 1.0.4, 包含在 `docs/` 目录下) 进行 API 通信。
    *   交互器设计中包含对 PLAXIS 命令行界面 (CLI) 的备用支持，但主要通过 API 驱动。
*   **数据处理:**
    *   项目文件: JSON 用于保存/加载项目设置。
    *   表格数据: Pandas 和 Openpyxl 用于潜在的数据操作和导出 (尽管当前导出为直接的 CSV)。
*   **绘图:** Matplotlib 用于生成荷载-贯入曲线。
*   **应用程序打包:** PyInstaller (脚本位于 `build.sh`)。
*   **测试:** Pytest 框架，以及 `pytest-qt` 和 `pytest-mock`。

##核心原理 / 架构

该应用程序在结构上分为前端 (GUI) 和后端 (逻辑与 PLAXIS 交互)。

```mermaid
graph TD
    A[用户界面 (Frontend - PySide6 - src/frontend/)] -->|用户操作, 数据模型| B(后端逻辑 - Python - src/backend/);
    B -->|命令, 控制, 数据| C(PLAXIS 交互器 - Python - src/backend/plaxis_interactor/interactor.py);
    C -->|Python 脚本 API / CLI| D[PLAXIS 3D 软件];

    subgraph A [用户界面]
        direction LR
        A1[项目管理];
        A2[输入组件];
        A3[执行控制 & 进度];
        A4[结果显示];
        A5[配置对话框];
    end

    subgraph B [后端逻辑]
        direction LR
        B1[数据模型];
        B2[项目 I/O];
        B3[输入验证];
        B4[分析工作器 QThread];
    end

    subgraph C [PLAXIS 交互器]
        direction LR
        C1[API 连接管理 (plxscripting)];
        C2[命令生成 (Builders)];
        C3[PLAXIS 操作执行];
        C4[结果提取 (Parsers)];
        C5[错误处理 & 日志];
    end
```

## 用户交互工作流

典型的用户交互流程如下：

1.  **启动与项目:** 用户启动应用程序，然后创建新项目或打开现有项目。
2.  **数据输入:** 用户通过 UI 各区域输入桩靴几何、土层、材料属性、加载条件和分析控制参数。
3.  **配置 (可选):** 用户可通过 文件 > 设置 来设定 PLAXIS 安装路径。
4.  **运行分析:** 用户点击“运行分析”。应用程序验证输入后，通过后端交互器启动 PLAXIS 分析过程。
5.  **监控:** 用户观察 UI 中显示的进度和日志。
6.  **查看与导出结果:** 分析完成后，显示结果（摘要、图表、表格）。用户可导出这些结果。
7.  **保存与退出:** 用户保存项目并退出应用。

```mermaid
sequenceDiagram
    actor 用户
    participant AppGUI as PlaxisSpudcanAutomator (前端)
    participant Backend as 后端逻辑 (AnalysisWorker)
    participant Interactor as PlaxisInteractor
    participant PlaxisAPI as PLAXIS 3D API (plxscripting)
    participant PlaxisEngine as PLAXIS 引擎

    用户->>AppGUI: 启动应用
    用户->>AppGUI: 新建/打开项目
    AppGUI-->>用户: 显示项目界面
    用户->>AppGUI: 输入参数 (桩靴, 土壤, 荷载, 控制)
    AppGUI-->>用户: 更新UI示意图/反馈
    用户->>AppGUI: 点击 "运行分析"
    AppGUI->>Backend: 开始分析 (附带 ProjectSettings)
    Backend->>Interactor: 初始化并运行工作流
    Interactor->>PlaxisAPI: 连接到服务器
    PlaxisAPI-->>Interactor: 连接成功/失败
    Interactor->>PlaxisAPI: 发送模型设置命令 (几何, 土壤)
    PlaxisAPI->>PlaxisEngine: 执行设置
    PlaxisEngine-->>PlaxisAPI: 设置完成
    Interactor->>PlaxisAPI: 发送计算命令 (网格, 阶段, 计算)
    PlaxisAPI->>PlaxisEngine: 执行计算
    loop 进度更新
        PlaxisEngine-->>PlaxisAPI: 进度/状态
        PlaxisAPI-->>Interactor: 转发进度
        Interactor-->>Backend: 发送进度信号
        Backend-->>AppGUI: 更新UI进度/日志
    end
    PlaxisEngine-->>PlaxisAPI: 计算完成, 原始结果
    PlaxisAPI-->>Interactor: 转发原始结果
    Interactor->>Interactor: 解析结果
    Interactor-->>Backend: 发送分析完成信号 (处理后结果)
    Backend-->>AppGUI: 显示结果 (图表, 表格, 摘要)
    用户->>AppGUI: 查看结果
    用户->>AppGUI: 导出数据 (可选)
    AppGUI-->>用户: 提供导出文件
    用户->>AppGUI: 保存项目
    AppGUI->>Backend: 保存项目数据 (到 .plaxauto)
    用户->>AppGUI: 退出
```

## 安装

1.  **先决条件:**
    *   Python (推荐 3.10+，开发使用 3.12)。确保 Python已添加到系统的 PATH 中。
    *   PLAXIS 3D: 已获得许可并正确安装的 PLAXIS 3D 版本，且该版本支持 Python 脚本 API。
    *   Git (用于克隆代码库)。

2.  **克隆代码库:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

3.  **创建虚拟环境 (推荐):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows 上: venv\Scripts\activate
    ```

4.  **安装 Python 依赖:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **安装 `plxscripting` 库:**
    本项目使用特定版本的 `plxscripting` 库，该库包含在 `docs/` 目录中。以可编辑模式安装它：
    ```bash
    pip install -e ./docs/plxscripting-1.0.4/
    ```

## 运行应用程序

1.  如果创建了虚拟环境，请确保已激活。
2.  导航到项目的根目录。
3.  运行主应用程序脚本:
    ```bash
    python -m src.main
    ```

**运行注意事项:**

*   **X Server 要求 (Linux/macOS):** 这是一个 GUI 应用程序，需要正在运行的 X Server 才能显示。
    *   在没有桌面环境的 Linux 系统上 (例如，无头服务器、某些 Docker 容器)，您可能需要使用 Xvfb (X 虚拟帧缓冲):
        ```bash
        # 安装 Xvfb (Debian/Ubuntu 示例)
        # sudo apt-get update && sudo apt-get install -y xvfb

        xvfb-run python -m src.main
        ```
*   **PLAXIS API 配置:**
    *   确保 PLAXIS API 服务已启用，并且在 PLAXIS 中正确配置了密码。
    *   应用程序将尝试使用默认端口 (输入: 10000, 输出: 10001) 和默认密码占位符连接到 `localhost` 上的 PLAXIS API。如果您的 PLAXIS API 设置不同，或者 `src/backend/plaxis_interactor/interactor.py` 中的默认密码 (`YOUR_API_PASSWORD`) 尚未更新，您可能需要在应用程序设置 (文件 > 设置) 中配置这些信息。
*   **PLAXIS 安装路径:** 应用程序可能需要您的 PLAXIS 安装可执行文件的路径。这通常可以在应用程序的 **文件 > 设置** 中设置。

## 构建应用程序

项目提供了一个 `build.sh` 脚本，用于使用 PyInstaller 创建独立的可执行文件。

1.  确保已安装 PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  使脚本可执行 (如果需要):
    ```bash
    chmod +x build.sh
    ```
3.  运行构建脚本:
    ```bash
    bash build.sh
    ```
    打包后的应用程序将位于 `dist/PlaxisSpudcanAutomator` 目录中。

## 运行测试

项目使用 `pytest` 进行测试。

1.  确保已安装测试依赖项 (它们包含在 `requirements.txt` 中)。
2.  导航到项目的根目录。
3.  运行测试:
    ```bash
    python -m pytest tests/
    ```

## 注意事项和已知问题

*   **`plxscripting library not found` 运行时警告:**
    运行 `python -m src.main` 时，控制台输出中可能会出现 "plxscripting library not found. PlaxisInteractor will not be able to connect to PLAXIS API." 的警告。尽管该库已通过 `pip install -e ./docs/plxscripting-1.0.4/` 正确安装，并且可以通过 `python -c "import plxscripting"` 进行验证，但此警告仍然存在。这表明在完整应用程序启动时，Python 路径或环境与直接导入测试时存在细微差别。虽然 GUI 可以启动，但这可能会影响 PLAXIS API 的连接性。如果直接的 PLAXIS 交互失败，则需要进一步调查。
*   **Qt XCB 平台插件问题 (Linux):**
    在某些 Linux 环境 (特别是最小化或无头环境) 中运行 Qt 应用程序可能会导致类似 "Could not load the Qt platform plugin 'xcb'" 的错误。为了在开发过程中以及在无头环境中使用 Xvfb 执行时解决这些问题，发现需要安装几个 XCB 和 XKB 相关的库。这些包括：
    *   `libxcb-cursor0`
    *   `libxkbcommon-x11-0`
    *   `libxcb-icccm4`
    *   `libxcb-image0`
    *   `libxcb-keysyms1`
    *   `libxcb-randr0`
    *   `libxcb-render-util0`
    *   `libxcb-shape0`
    *   `libxcb-xfixes0`
    *   以及用于在无头环境中运行的 `xvfb` 本身。
    如果您遇到类似的 Qt 平台问题，请确保已安装这些库 (或适用于您发行版的等效库)。
*   **PLAXIS 软件依赖:** 此工具的全部功能 (即运行实际分析) 取决于已获得许可且正常工作的 PLAXIS 3D 安装，并且其 Python 脚本 API 已启用且可访问。

```
