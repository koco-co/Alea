"use client";

import Link from "next/link";
import { useState } from "react";

const initialFollowing = [
  { id: "match-104", title: "西班牙 vs 阿根廷", meta: "2026 世界杯决赛 · 07-20 03:00" },
  { id: "prediction-n8c4", title: "公证预测 N8C4-02", meta: "圆桌共识 2 : 1 · 已发布" },
];

export default function PersonalSettingsPage() {
  const [following, setFollowing] = useState(initialFollowing);
  const [saved, setSaved] = useState(false);
  return <main className="console-main settings-page"><div className="page-heading research-heading"><div><p className="eyebrow">个人设置</p><h1>只接收真正关心的变化。</h1><p>通知仅由显式关注触发；查看、采纳或打开详情不会自动订阅。</p></div><Link className="button secondary" href="/console/settings/security">账户安全</Link></div><div className="personal-settings-layout"><nav><a className="active" href="#notifications">通知偏好</a><a href="#following">我的关注</a><Link href="/console/settings/security">账户安全</Link></nav><div><section className="personal-panel" id="notifications"><div className="panel-heading"><div><p className="eyebrow">通知偏好</p><h2>站内消息</h2></div><span className={saved ? "status-chip" : "status-chip"}>{saved ? "已保存" : "自动保存"}</span></div><div className="preference-list"><label className="switch-row"><input type="checkbox" defaultChecked onChange={() => setSaved(true)} /><span><strong>新预测卡发布</strong><small>平台发布新的可见预测卡时通知</small></span></label><label className="switch-row"><input type="checkbox" defaultChecked onChange={() => setSaved(true)} /><span><strong>关注卡片开奖</strong><small>所有腿进入结算终态后统一通知</small></span></label><label className="switch-row"><input type="checkbox" defaultChecked onChange={() => setSaved(true)} /><span><strong>关注卡片复盘发布</strong><small>已关注预测的复盘通过审核时通知</small></span></label></div><div className="settings-note">当前仅提供站内消息。邮件、短信与微信推送不在首版范围内。</div></section><section className="personal-panel" id="following"><div className="panel-heading"><div><p className="eyebrow">我的关注</p><h2>{following.length} 个显式关注</h2></div></div>{following.length ? <div className="following-list">{following.map((item) => <div key={item.id}><span><strong>{item.title}</strong><small>{item.meta}</small></span><button className="button secondary" type="button" onClick={() => setFollowing((items) => items.filter((entry) => entry.id !== item.id))}>取消关注</button></div>)}</div> : <div className="wide-empty-state"><strong>还没有关注</strong><p>在比赛或预测卡上点击“关注”后，会集中显示在这里。</p></div>}</section></div></div></main>;
}
