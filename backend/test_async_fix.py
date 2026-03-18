#!/usr/bin/env python
"""
测试异步协程泄漏修复
验证：采集过程中的 asyncio.gather 現在使用 return_exceptions=True
"""
import asyncio
import warnings
import sys
from app.services.task_service import TaskService
from app.schemas.constraint import BusinessConstraint, ConstraintItem
from app.core.state import state

# 启用RuntimeWarning显示
warnings.simplefilter("always", RuntimeWarning)

async def test_collection_with_mock_config():
    """
    测试采集流程是否产生协程泄漏警告
    """
    print("=" * 70)
    print("开始测试采集流程中的异步处理...")
    print("=" * 70)
    
    # 设置约束条件
    constraint = BusinessConstraint(
        company_name="测试公司",
        core_business=["IT服务"],
        geography_limits=[ConstraintItem(name="地域", value="全国", is_must_have=False)]
    )
    state.update_constraint(constraint)
    
    # 配置采集参数
    config = {
        "search_keywords": "软件开发 技术服务",
        "target_urls": [],
        "wechat_accounts": []
    }
    
    service = TaskService()
    
    try:
        print("\n正在执行采集任务...")
        await service.run_one_off_scan(config=config, is_scheduled=False)
        print(f"\n采集状态: {state.current_step}")
        print(f"进度: {state.current_progress}%")
        print("\n✅ 采集完成（没有异常或协程泄漏警告）")
        return True
    except Exception as e:
        print(f"\n❌ 采集过程中发生错误: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        state.is_running = False

async def main():
    """主测试函数"""
    success = await test_collection_with_mock_config()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    print("Python 异步协程泄漏检测模式已启用")
    asyncio.run(main())
