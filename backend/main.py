"""
VikingDB 会话记忆完整示例
包含初始化、写入会话数据和检索会话记忆的完整流程
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from vikingdb import IAM
from vikingdb.memory import VikingMem
from vikingdb.memory.exceptions import VikingMemException

# 加载 .env 文件中的环境变量
load_dotenv()

def init_memory_client():
    """初始化记忆库客户端"""
    print("=== 初始化 VikingDB 客户端 ===")
    
    # 认证配置
    ak = os.getenv("VIKINGDB_AK")
    sk = os.getenv("VIKINGDB_SK")
    if not ak or not sk:
        raise ValueError("请设置环境变量 VIKINGDB_AK 和 VIKINGDB_SK")
    _auth = IAM(ak=ak, sk=sk)
    
    # 创建客户端
    client = VikingMem(
        host="api-knowledgebase.mlp.cn-beijing.volces.com",
        region="cn-beijing",
        auth=_auth,
        scheme="http",
    )
    
    print("客户端初始化成功")
    return client
def get_or_create_collection(client, collection_name, project_name="default"):
    """获取或创建记忆库集合"""
    print(f"\n=== 获取记忆库集合: {collection_name} ===")
    
    try:
        # 尝试获取已存在的集合
        collection = client.get_collection(
            collection_name=collection_name,
            project_name=project_name
        )
        print(f"成功获取现有集合: {collection_name}")
        return collection
        
    except VikingMemException as e:
        print(f"获取集合失败: {e.message}")
        raise

def add_memory_sessions(collection, memory_sessions):
    """
    使用真实对话添加会话记忆数据。

    参数说明：
    - collection: VikingDB 记忆库集合实例
    - memory_sessions: List[dict]，每个元素形如：
        {
            "session_id": "业务侧的会话ID",
            "user_id": "user_001",
            "assistant_id": "assistant_001",
            "messages": [
                {"role": "user", "content": "用户说的话"},
                {"role": "assistant", "content": "助手的回复"},
                ...
            ],
            # 可选，额外元数据
            "metadata": {
                "channel": "web",
                "biz_tags": ["order", "coffee"]
            }
        }

    你可以在真实对话结束后，将该轮完整对话整理为上述结构，传入本方法，
    从而用真实会话更新历史会话记忆，而不是依赖固定的 mock 数据。
    """
    print(f"\n=== 添加会话记忆（真实对话） ===")

    if not memory_sessions:
        print("未收到任何会话数据，跳过写入。")
        return []

    results = []
    total = len(memory_sessions)

    for i, session_data in enumerate(memory_sessions, 1):
        # 基础校验与默认值填充
        session_id = session_data.get("session_id")
        messages = session_data.get("messages") or []
        user_id = session_data.get("user_id", "user_001")
        assistant_id = session_data.get("assistant_id", "assistant_001")

        if not session_id or not messages:
            print(f"会话 {i}/{total} 缺少 session_id 或 messages，已跳过。")
            continue

        base_metadata = {
            "default_user_id": user_id,
            "default_assistant_id": assistant_id,
            "time": int(datetime.now().timestamp() * 1000),
        }
        extra_metadata = session_data.get("metadata") or {}
        # 业务侧可通过 metadata 扩展字段，这里做一个浅合并
        base_metadata.update(extra_metadata)

        try:
            print(f"添加会话 {i}/{total}，session_id={session_id} ...")

            result = collection.add_session(
                session_id=session_id,
                messages=messages,
                metadata=base_metadata
            )

            results.append(result)
            print(f"会话 {i}/{total} 添加成功")

        except VikingMemException as e:
            print(f"会话 {i}/{total} 添加失败: {e.message}")
            continue

    print(f"成功添加 {len(results)}/{total} 个会话记忆")
    return results

def add_user_profile(
    collection,
    user_id,
    assistant_id="assistant_001",
    user_profile_text=None,
    profile_type="profile_v1",
    is_upsert=True,
):
    """
    使用真实对话抽取的用户画像文本，更新 VikingDB 中的用户画像。

    建议配合对话系统中基于大模型的画像抽取逻辑使用：
    - 在业务服务中（例如本项目的 server.py 中），
      基于「历史画像 + 本轮问答」生成新的画像文本 user_profile_text，
      然后调用本方法进行写入/更新。

    参数说明：
    - collection: VikingDB 记忆库集合实例
    - user_id: 业务侧用户ID
    - assistant_id: 助手ID，默认为 "assistant_001"
    - user_profile_text: 基于真实对话生成的完整画像文本（字符串）
    - profile_type: 画像类型，默认为 "profile_v1"
    - is_upsert: 是否走 upsert 逻辑，默认为 True（不存在则创建，存在则更新）
    """
    print(f"\n=== 更新用户画像（真实对话） ===")

    if not user_profile_text or not str(user_profile_text).strip():
        print("未提供用户画像文本，跳过画像写入。")
        return None

    memory_info = {
        "user_profile": str(user_profile_text).strip()
    }

    try:
        result = collection.add_profile(
            profile_type=profile_type,
            user_id=user_id,
            assistant_id=assistant_id,
            memory_info=memory_info,
            is_upsert=is_upsert,
        )

        print("用户画像写入/更新成功")
        return result

    except VikingMemException as e:
        print(f"用户画像写入失败: {e.message}")
        raise

def search_memories(collection):
    """搜索会话记忆数据"""
    print(f"\n=== 会话记忆搜索演示 ===")
    
    # 基础搜索 - 按用户ID和关键词
    print("\n--- 搜索用户001的会话记忆 ---")
    try:
        result = collection.search_memory(
            query="咖啡",
            filter={
                "memory_type": ["profile_v1", "event_v1"],
                "user_id": "user_001",
                "assistant_id": "assistant_001"
            },
            limit=10
        )
        
        if result and isinstance(result, dict) and result.get('data'):
            result_data = result['data']
            count = result_data.get('count', 0)
            print(f"找到 {count} 个结果")
            
            if count > 0 and 'result_list' in result_data:
                for item in result_data['result_list'][:3]:
                    print(f"- 结果: {item}")
            else:
                print("结果列表为空")
        else:
            print("未找到相关结果")
            
    except VikingMemException as e:
        print(f"搜索失败: {e.message}")
    
def main():
    """主函数 - 完整流程演示"""
    print("VikingDB 会话记忆完整示例开始")
    print("=" * 50)
    
    try:
        # 1. 初始化客户端
        client = init_memory_client()
        
        # 2. 获取集合（使用现有集合）
        collection = get_or_create_collection(
            client, 
            collection_name="dogbot", #替换为您的记忆库名称
            project_name="default"
        )
        
        # 3. 搜索记忆（演示查询）。真实业务中：
        #    - 在对话服务中调用 add_memory_sessions() 写入每轮真实会话；
        #    - 在画像抽取服务中调用 add_user_profile() 基于真实对话更新画像。
        search_memories(collection)
        
        print("完整示例执行成功")
        print("总结:")
        print("- 客户端初始化成功")
        print("- 可在业务服务中基于真实对话调用 add_memory_sessions / add_user_profile")
        print("- 会话记忆搜索功能正常（search_memories 示例）")
        
    except VikingMemException as e:
        print(f"VikingDB异常: {e.message}")
        
    except Exception as e:
        print(f"异常: {str(e)}")
        
    finally:
        print("=" * 50)
        print("示例执行完成")

if __name__ == "__main__":
    main()