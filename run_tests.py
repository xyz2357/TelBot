#!/usr/bin/env python3
# run_tests.py
"""
测试运行器脚本
提供各种测试运行模式和报告生成功能
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
import time
from datetime import datetime


class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests" 
        self.reports_dir = self.project_root / "reports"
        self.coverage_dir = self.project_root / "htmlcov"
        
        # 创建必要的目录
        self.reports_dir.mkdir(exist_ok=True)
        self.tests_dir.mkdir(exist_ok=True)
    
    def run_unit_tests(self, verbose: bool = True, coverage: bool = True) -> int:
        """运行单元测试"""
        print("🧪 运行单元测试...")
        
        cmd = ["python", "-m", "pytest", "tests/test_unit.py"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=.",
                "--cov-report=html:htmlcov/unit",
                "--cov-report=term-missing",
                "--cov-report=xml:reports/unit_coverage.xml"
            ])
        
        cmd.extend([
            "--html=reports/unit_tests.html",
            "--self-contained-html",
            "-m", "unit"
        ])
        
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_integration_tests(self, verbose: bool = True, coverage: bool = True) -> int:
        """运行集成测试"""
        print("🔗 运行集成测试...")
        
        cmd = ["python", "-m", "pytest", "tests/test_integration.py"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=.",
                "--cov-report=html:htmlcov/integration", 
                "--cov-report=term-missing",
                "--cov-report=xml:reports/integration_coverage.xml"
            ])
        
        cmd.extend([
            "--html=reports/integration_tests.html",
            "--self-contained-html",
            "-m", "integration"
        ])
        
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_e2e_tests(self, verbose: bool = True) -> int:
        """运行端到端测试"""
        print("🎯 运行端到端测试...")
        
        cmd = ["python", "-m", "pytest", "tests/test_e2e.py"]
        
        if verbose:
            cmd.append("-v")
        
        cmd.extend([
            "--html=reports/e2e_tests.html", 
            "--self-contained-html",
            "-m", "e2e"
        ])
        
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_all_tests(self, verbose: bool = True, coverage: bool = True, parallel: bool = False) -> int:
        """运行所有测试"""
        print("🚀 运行完整测试套件...")
        
        cmd = ["python", "-m", "pytest", "tests/"]
        
        if verbose:
            cmd.append("-v")
        
        if parallel:
            cmd.extend(["-n", "auto"])  # 需要pytest-xdist
        
        if coverage:
            cmd.extend([
                "--cov=.",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing", 
                "--cov-report=xml:reports/coverage.xml"
            ])
        
        cmd.extend([
            "--html=reports/all_tests.html",
            "--self-contained-html",
            "--junitxml=reports/junit.xml"
        ])
        
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_performance_tests(self) -> int:
        """运行性能测试"""
        print("⚡ 运行性能测试...")
        
        cmd = [
            "python", "-m", "pytest", "tests/",
            "-v",
            "-m", "slow",
            "--html=reports/performance_tests.html",
            "--self-contained-html"
        ]
        
        return subprocess.run(cmd, cwd=self.project_root).returncode
    
    def run_security_tests(self) -> int:
        """运行安全测试"""
        print("🔒 运行安全测试...")
        
        # 使用bandit进行安全扫描
        bandit_cmd = [
            "bandit", "-r", ".",
            "-f", "json", 
            "-o", "reports/security_report.json",
            "--exclude", "tests/,venv/,env/"
        ]
        
        bandit_result = subprocess.run(bandit_cmd, cwd=self.project_root)
        
        # 运行安全相关的单元测试
        pytest_cmd = [
            "python", "-m", "pytest", "tests/",
            "-v",
            "-k", "security or auth",
            "--html=reports/security_tests.html",
            "--self-contained-html"
        ]
        
        pytest_result = subprocess.run(pytest_cmd, cwd=self.project_root)
        
        return max(bandit_result.returncode, pytest_result.returncode)
    
    def run_code_quality_checks(self) -> int:
        """运行代码质量检查"""
        print("📊 运行代码质量检查...")
        
        results = []
        
        # Black代码格式检查
        print("  检查代码格式 (Black)...")
        black_result = subprocess.run([
            "black", "--check", "--diff", "."
        ], cwd=self.project_root)
        results.append(black_result.returncode)
        
        # Flake8代码风格检查
        print("  检查代码风格 (Flake8)...")
        flake8_result = subprocess.run([
            "flake8", ".", 
            "--output-file=reports/flake8_report.txt",
            "--exclude=venv,env,__pycache__"
        ], cwd=self.project_root)
        results.append(flake8_result.returncode)
        
        # MyPy类型检查
        print("  检查类型注解 (MyPy)...")
        mypy_result = subprocess.run([
            "mypy", ".",
            "--ignore-missing-imports",
            "--html-report", "reports/mypy_report"
        ], cwd=self.project_root)
        results.append(mypy_result.returncode)
        
        return max(results)
    
    def generate_test_report(self) -> None:
        """生成测试总结报告"""
        print("📋 生成测试报告...")
        
        report_content = self._generate_html_report()
        
        report_path = self.reports_dir / "test_summary.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ 测试报告已生成: {report_path}")
    
    def _generate_html_report(self) -> str:
        """生成HTML格式的测试报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查各种报告文件是否存在
        reports = {
            "单元测试": self.reports_dir / "unit_tests.html",
            "集成测试": self.reports_dir / "integration_tests.html", 
            "端到端测试": self.reports_dir / "e2e_tests.html",
            "完整测试": self.reports_dir / "all_tests.html",
            "性能测试": self.reports_dir / "performance_tests.html",
            "安全测试": self.reports_dir / "security_tests.html"
        }
        
        coverage_reports = {
            "总体覆盖率": self.coverage_dir / "index.html",
            "单元测试覆盖率": Path("htmlcov/unit/index.html"),
            "集成测试覆盖率": Path("htmlcov/integration/index.html")
        }
        
        quality_reports = {
            "Flake8报告": self.reports_dir / "flake8_report.txt",
            "MyPy报告": self.reports_dir / "mypy_report" / "index.html",
            "安全扫描": self.reports_dir / "security_report.json"
        }
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stable Diffusion Bot - 测试报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .section {{
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .report-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .report-card {{
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 8px;
            background: #fafafa;
        }}
        .report-card h3 {{
            margin-top: 0;
            color: #555;
        }}
        .available {{
            color: #28a745;
            font-weight: bold;
        }}
        .unavailable {{
            color: #dc3545;
            font-weight: bold;
        }}
        .link {{
            color: #007bff;
            text-decoration: none;
            font-weight: 500;
        }}
        .link:hover {{
            text-decoration: underline;
        }}
        .timestamp {{
            text-align: center;
            color: #666;
            font-style: italic;
            margin-top: 30px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .stat {{
            text-align: center;
            padding: 10px;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎨 Stable Diffusion Telegram Bot</h1>
        <h2>测试报告总览</h2>
        <p>自动化测试执行结果与代码质量报告</p>
    </div>

    <div class="section">
        <h2>📊 测试统计</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-number">{len([r for r in reports.values() if r.exists()])}</div>
                <div class="stat-label">测试报告</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len([r for r in coverage_reports.values() if r.exists()])}</div>
                <div class="stat-label">覆盖率报告</div>
            </div>
            <div class="stat">
                <div class="stat-number">{len([r for r in quality_reports.values() if r.exists()])}</div>
                <div class="stat-label">质量报告</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🧪 测试报告</h2>
        <div class="report-grid">
        """
        
        for name, path in reports.items():
            if path.exists():
                status = '<span class="available">✅ 可用</span>'
                link = f'<a href="{path.name}" class="link">查看报告</a>'
            else:
                status = '<span class="unavailable">❌ 未生成</span>'
                link = '未执行此测试'
            
            html_content += f"""
            <div class="report-card">
                <h3>{name}</h3>
                <p>状态: {status}</p>
                <p>{link}</p>
            </div>
            """
        
        html_content += """
        </div>
    </div>

    <div class="section">
        <h2>📈 代码覆盖率报告</h2>
        <div class="report-grid">
        """
        
        for name, path in coverage_reports.items():
            if path.exists():
                status = '<span class="available">✅ 可用</span>'
                link = f'<a href="{path}" class="link">查看覆盖率</a>'
            else:
                status = '<span class="unavailable">❌ 未生成</span>'
                link = '未生成覆盖率报告'
            
            html_content += f"""
            <div class="report-card">
                <h3>{name}</h3>
                <p>状态: {status}</p>
                <p>{link}</p>
            </div>
            """
        
        html_content += """
        </div>
    </div>

    <div class="section">
        <h2>🔍 代码质量报告</h2>
        <div class="report-grid">
        """
        
        for name, path in quality_reports.items():
            if path.exists():
                status = '<span class="available">✅ 可用</span>'
                if path.suffix == '.json':
                    link = '查看JSON报告'
                elif path.suffix == '.txt':
                    link = f'<a href="{path.name}" class="link">查看文本报告</a>'
                else:
                    link = f'<a href="{path}/index.html" class="link">查看报告</a>'
            else:
                status = '<span class="unavailable">❌ 未生成</span>'
                link = '未执行质量检查'
            
            html_content += f"""
            <div class="report-card">
                <h3>{name}</h3>
                <p>状态: {status}</p>
                <p>{link}</p>
            </div>
            """
        
        html_content += f"""
        </div>
    </div>

    <div class="section">
        <h2>📝 测试执行说明</h2>
        <h3>如何运行测试:</h3>
        <pre><code># 运行所有测试
python run_tests.py --all

# 仅运行单元测试
python run_tests.py --unit

# 运行集成测试
python run_tests.py --integration

# 运行端到端测试
python run_tests.py --e2e

# 运行性能测试
python run_tests.py --performance

# 运行代码质量检查
python run_tests.py --quality</code></pre>

        <h3>测试文件说明:</h3>
        <ul>
            <li><strong>test_unit.py</strong> - 单元测试，测试各个模块的独立功能</li>
            <li><strong>test_integration.py</strong> - 集成测试，测试模块间的交互</li>
            <li><strong>test_e2e.py</strong> - 端到端测试，测试完整的用户操作流程</li>
            <li><strong>factories.py</strong> - 测试数据工厂和Mock工具</li>
        </ul>
    </div>

    <div class="timestamp">
        <p>报告生成时间: {timestamp}</p>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def clean_reports(self) -> None:
        """清理旧的测试报告"""
        print("🧹 清理旧测试报告...")
        
        if self.reports_dir.exists():
            shutil.rmtree(self.reports_dir)
        if self.coverage_dir.exists():
            shutil.rmtree(self.coverage_dir)
        
        self.reports_dir.mkdir(exist_ok=True)
        
        print("✅ 清理完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Stable Diffusion Bot 测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_tests.py --all              # 运行所有测试
  python run_tests.py --unit --coverage  # 运行单元测试并生成覆盖率报告
  python run_tests.py --quality          # 运行代码质量检查
  python run_tests.py --clean            # 清理测试报告
        """
    )
    
    # 测试类型选项
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--e2e', action='store_true', help='运行端到端测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    parser.add_argument('--security', action='store_true', help='运行安全测试')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    
    # 代码质量选项
    parser.add_argument('--quality', action='store_true', help='运行代码质量检查')
    
    # 其他选项
    parser.add_argument('--no-coverage', action='store_true', help='禁用覆盖率报告')
    parser.add_argument('--parallel', action='store_true', help='并行运行测试')
    parser.add_argument('--quiet', action='store_true', help='静默模式')
    parser.add_argument('--clean', action='store_true', help='清理旧报告')
    parser.add_argument('--report', action='store_true', help='仅生成测试报告')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # 检查是否安装了必要的依赖
    try:
        import pytest
    except ImportError:
        print("❌ 请先安装测试依赖: pip install -r test_requirements.txt")
        return 1
    
    start_time = time.time()
    results = []
    
    try:
        if args.clean:
            runner.clean_reports()
            return 0
        
        if args.report:
            runner.generate_test_report()
            return 0
        
        coverage = not args.no_coverage
        verbose = not args.quiet
        
        if args.unit or args.all:
            results.append(runner.run_unit_tests(verbose, coverage))
        
        if args.integration or args.all:
            results.append(runner.run_integration_tests(verbose, coverage))
        
        if args.e2e or args.all:
            results.append(runner.run_e2e_tests(verbose))
        
        if args.performance or args.all:
            results.append(runner.run_performance_tests())
        
        if args.security or args.all:
            results.append(runner.run_security_tests())
        
        if args.quality:
            results.append(runner.run_code_quality_checks())
        
        # 如果没有指定任何测试类型，运行所有测试
        if not any([args.unit, args.integration, args.e2e, args.performance, args.security, args.all, args.quality]):
            results.append(runner.run_all_tests(verbose, coverage, args.parallel))
        
        # 生成测试报告
        runner.generate_test_report()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 输出结果摘要
        print(f"\n{'='*60}")
        print(f"📊 测试执行摘要")
        print(f"{'='*60}")
        print(f"⏱️  执行时间: {duration:.2f}秒")
        print(f"✅ 成功: {results.count(0)}")
        print(f"❌ 失败: {len(results) - results.count(0)}")
        
        if all(result == 0 for result in results):
            print(f"🎉 所有测试通过!")
            return 0
        else:
            print(f"⚠️  部分测试失败")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⛔ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())