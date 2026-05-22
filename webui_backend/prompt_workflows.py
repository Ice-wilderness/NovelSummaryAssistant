from __future__ import annotations

from string import Formatter
from typing import Dict, Iterable, List

from logic.prompts import DEFAULT_PROMPTS

from .config_models import (
    PromptMessage,
    PromptModule,
    PromptNode,
    PromptWorkflow,
    WorkflowPromptConfig,
)


PROMPT_CONFIG_VERSION = 1

PROMPT_MODULE_DEFINITIONS = [
    {
        "id": "general_prepend_prompt",
        "name": "通用前置提示",
        "description": "可在任意节点中引用的通用输出约束，默认来自旧版通用前置提示词。",
        "prompt_key": "general_prepend_prompt",
    }
]

PROMPT_WORKFLOW_DEFINITIONS = [
    {
        "id": "novel_summary",
        "title": "小说总结",
        "description": "覆盖章节小总结、剧情/角色大总结、超级总结和终极总结的提示词节点。",
        "nodes": [
            ("prompt_small_summary", "章节小总结", "对单个章节生成剧情与角色信息总结。"),
            ("prompt_big_plot", "剧情大总结", "整合一批剧情小总结，形成阶段性剧情设定总结。"),
            ("prompt_big_char", "角色大总结", "整合一批角色信息块，形成阶段性角色总结。"),
            ("prompt_super_plot_p1", "超级剧情 P1", "生成世界观与核心设定总览。"),
            ("prompt_super_plot_p2", "超级剧情 P2", "生成详细剧情线路总览。"),
            ("prompt_super_char_p1", "超级角色 P1", "生成主要角色深度剖析。"),
            ("prompt_super_char_p2", "超级角色 P2", "生成次要角色与关系网络。"),
            ("prompt_ultimate_plot_p1", "终极剧情 P1", "生成最终剧情总览中的世界观与核心设定部分。"),
            ("prompt_ultimate_plot_p2", "终极剧情 P2", "生成最终剧情总览中的完整剧情脉络部分。"),
            ("prompt_ultimate_char_p1", "终极角色 P1", "生成最终角色档案中的核心人物详录。"),
            ("prompt_ultimate_char_p2", "终极角色 P2", "生成最终角色档案中的次要角色和关系网。"),
        ],
    },
    {
        "id": "article_summary",
        "title": "文章总结",
        "description": "覆盖文档分段摘要和最终整合摘要的提示词节点。",
        "nodes": [
            ("prompt_article_section", "分段摘要", "对单个文章或文档片段生成独立摘要。"),
            ("prompt_article_final", "最终摘要", "整合所有分段摘要，生成完整文档摘要和核心要点。"),
        ],
    },
    {
        "id": "trigger_scan",
        "title": "雷点扫描",
        "description": "覆盖粗筛、精确扫描、二次验证和事件聚合的提示词节点。",
        "nodes": [
            ("trigger_coarse_scan", "粗筛", "根据小总结批次筛出需要进一步检查的章节范围。"),
            ("trigger_precise_scan", "精确扫描", "在带段落编号的章节原文中定位雷点和证据。"),
            ("trigger_verification", "二次验证", "独立复核首轮发现并给出保留或剔除理由。"),
            ("trigger_aggregation", "事件聚合", "将段落级发现合并为可阅读的雷点事件。"),
        ],
    },
    {
        "id": "custom_summary",
        "title": "自定义总结",
        "description": "自定义总结当前使用运行时输入的用户指令，不维护持久化默认提示词节点。",
        "empty_message": "自定义总结的提示词来自任务页面的“自定义指令”，暂无持久化节点。",
        "nodes": [],
    },
    {
        "id": "chapter_split",
        "title": "章节分割",
        "description": "章节分割不调用 LLM，不需要配置提示词节点。",
        "empty_message": "章节分割使用规则和正则处理文本，不使用 LLM 提示词。",
        "nodes": [],
    },
]


def extract_prompt_variables(text: str) -> List[str]:
    variables: set[str] = set()
    for _, field_name, _, _ in Formatter().parse(text):
        if not field_name:
            continue
        root_name = field_name.split(".", 1)[0].split("[", 1)[0]
        if root_name:
            variables.add(root_name)
    return sorted(variables)


def create_default_prompt_node(prompt_key: str, title: str, description: str) -> PromptNode:
    prompt_config = DEFAULT_PROMPTS[prompt_key]
    default_text = str(prompt_config["default"])
    variables = set(extract_prompt_variables(default_text))
    variables.update(str(key) for key in prompt_config.get("vars", {}).keys())
    message = PromptMessage(
        id=f"{prompt_key}_message_1",
        role="user",
        content=default_text,
    )
    return PromptNode(
        id=prompt_key,
        prompt_key=prompt_key,
        filename=str(prompt_config["filename"]),
        title=title,
        description=description,
        variables=sorted(variables),
        messages=[message],
        default_messages=[PromptMessage.from_dict(message.to_dict())],
    )


def create_default_prompt_modules() -> List[PromptModule]:
    modules: List[PromptModule] = []
    for definition in PROMPT_MODULE_DEFINITIONS:
        prompt_config = DEFAULT_PROMPTS[definition["prompt_key"]]
        default_text = str(prompt_config["default"])
        message = PromptMessage(
            id=f"{definition['id']}_message_1",
            role="user",
            content=default_text,
        )
        modules.append(
            PromptModule(
                id=definition["id"],
                name=definition["name"],
                description=definition["description"],
                content=default_text,
                default_content=default_text,
                messages=[message],
                default_messages=[PromptMessage.from_dict(message.to_dict())],
            )
        )
    return modules


def create_default_workflows(
    workflow_definitions: Iterable[Dict] = PROMPT_WORKFLOW_DEFINITIONS,
) -> List[PromptWorkflow]:
    workflows: List[PromptWorkflow] = []
    for definition in workflow_definitions:
        workflows.append(
            PromptWorkflow(
                id=str(definition["id"]),
                title=str(definition["title"]),
                description=str(definition.get("description", "")),
                empty_message=str(definition.get("empty_message", "")),
                nodes=[
                    create_default_prompt_node(prompt_key, title, description)
                    for prompt_key, title, description in definition.get("nodes", [])
                ],
            )
        )
    return workflows


def create_default_workflow_prompt_config(source: str = "defaults") -> WorkflowPromptConfig:
    return WorkflowPromptConfig(
        version=PROMPT_CONFIG_VERSION,
        source=source,
        workflows=create_default_workflows(),
        modules=create_default_prompt_modules(),
    )
