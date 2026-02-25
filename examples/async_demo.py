#!/usr/bin/env python3
"""
async 关键字演示示例
"""

import asyncio
import time
from typing import List


# 同步函数示例（会阻塞）
def sync_fetch_data(url: str) -> str:
    """模拟同步网络请求 - 会阻塞程序执行"""
    print(f"开始获取数据: {url}")
    time.sleep(2)  # 模拟网络延迟
    print(f"完成获取数据: {url}")
    return f"数据来自 {url}"


# 异步函数示例（不会阻塞）
async def async_fetch_data(url: str) -> str:
    """模拟异步网络请求 - 不会阻塞程序执行"""
    print(f"开始异步获取数据: {url}")
    await asyncio.sleep(2)  # 异步等待，不阻塞其他任务
    print(f"完成异步获取数据: {url}")
    return f"异步数据来自 {url}"


# 同步方式调用多个请求
def sync_example():
    """同步执行示例 - 总耗时约 6 秒"""
    print("=== 同步执行示例 ===")
    start_time = time.time()
    
    urls = ["网站A", "网站B", "网站C"]
    results = []
    
    for url in urls:
        result = sync_fetch_data(url)
        results.append(result)
    
    end_time = time.time()
    print(f"同步执行完成，总耗时: {end_time - start_time:.2f} 秒")
    print(f"结果: {results}")
    print()


# 异步方式调用多个请求
async def async_example():
    """异步执行示例 - 总耗时约 2 秒"""
    print("=== 异步执行示例 ===")
    start_time = time.time()
    
    urls = ["网站A", "网站B", "网站C"]
    
    # 创建多个异步任务
    tasks = [async_fetch_data(url) for url in urls]
    
    # 并发执行所有任务
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    print(f"异步执行完成，总耗时: {end_time - start_time:.2f} 秒")
    print(f"结果: {results}")
    print()


# 异步生成器示例
async def async_generator_example():
    """异步生成器示例"""
    print("=== 异步生成器示例 ===")
    
    async def async_numbers():
        for i in range(5):
            await asyncio.sleep(0.5)  # 模拟异步操作
            yield i
    
    # 使用异步生成器
    async for num in async_numbers():
        print(f"接收到数字: {num}")
    print()


# 在您的项目中使用的实际例子
async def real_world_example():
    """在实际项目中使用 async 的场景"""
    print("=== 实际应用场景 ===")
    
    # 模拟数据库查询和外部API调用
    async def mock_db_query():
        await asyncio.sleep(0.1)
        return "用户数据"
    
    async def mock_api_call():
        await asyncio.sleep(0.2)
        return "天气信息"
    
    async def mock_llm_call():
        await asyncio.sleep(0.3)
        return "AI回复"
    
    # 并发执行多个异步操作
    db_task = mock_db_query()
    api_task = mock_api_call()
    llm_task = mock_llm_call()
    
    # 等待所有任务完成
    db_result, api_result, llm_result = await asyncio.gather(db_task, api_task, llm_task)
    
    print(f"数据库结果: {db_result}")
    print(f"API结果: {api_result}")
    print(f"LLM结果: {llm_result}")
    print()


def main():
    """主函数"""
    print("Python async/await 演示")
    print("=" * 50)
    
    # 运行同步示例
    sync_example()
    
    # 运行异步示例
    asyncio.run(async_example())
    
    # 运行异步生成器示例
    asyncio.run(async_generator_example())
    
    # 运行实际应用示例
    asyncio.run(real_world_example())
    
    print("演示完成！")


if __name__ == "__main__":
    main()