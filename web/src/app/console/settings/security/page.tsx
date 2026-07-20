"use client";

import Link from "next/link";
import { useState } from "react";

export default function SecuritySettingsPage() {
  const [message, setMessage] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  return (
    <main className="console-main settings-page">
      <Link className="button secondary back-link" href="/console/settings">
        返回个人设置
      </Link>
      <div className="page-heading research-heading">
        <div>
          <p className="eyebrow">账户安全</p>
          <h1>登录方式与账户控制。</h1>
          <p>
            敏感操作需要重新验证；注销后可识别账户数据删除，系统审计主体改为不可逆匿名标识。
          </p>
        </div>
        <span className="status-chip">账户正常</span>
      </div>
      <div className="security-grid">
        <section className="personal-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">密码</p>
              <h2>修改登录密码</h2>
            </div>
          </div>
          <form
            className="security-form"
            onSubmit={(event) => {
              event.preventDefault();
              setMessage("密码更新请求已提交");
            }}
          >
            <label>
              <span>当前密码</span>
              <input type="password" autoComplete="current-password" />
            </label>
            <label>
              <span>新密码</span>
              <input
                type="password"
                autoComplete="new-password"
                minLength={10}
              />
            </label>
            <label>
              <span>确认新密码</span>
              <input
                type="password"
                autoComplete="new-password"
                minLength={10}
              />
            </label>
            <button className="button primary inline" type="submit">
              更新密码
            </button>
          </form>
        </section>
        <section className="personal-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">第三方账户</p>
              <h2>OAuth 绑定</h2>
            </div>
          </div>
          <div className="oauth-list">
            <div>
              <span>
                <strong>GitHub</strong>
                <small>尚未绑定</small>
              </span>
              <button
                className="button secondary"
                type="button"
                onClick={() => setMessage("即将跳转 GitHub 授权")}
              >
                绑定
              </button>
            </div>
            <div>
              <span>
                <strong>Google</strong>
                <small>lin@example.com · 已绑定</small>
              </span>
              <button
                className="button secondary"
                type="button"
                onClick={() => setMessage("解绑前需要重新验证")}
              >
                解绑
              </button>
            </div>
          </div>
        </section>
        <section className="personal-panel danger-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">危险操作</p>
              <h2>注销账户</h2>
            </div>
          </div>
          <p>
            将删除 Auth
            用户、个人资料、关注、通知与通知偏好。预测与系统审计中的主体会匿名化，不保留邮箱或
            OAuth ID。
          </p>
          <button
            className="button danger"
            type="button"
            onClick={() => setConfirmDelete(true)}
          >
            申请注销账户
          </button>
        </section>
      </div>
      {message ? (
        <div className="toast-message" role="status">
          {message}
        </div>
      ) : null}
      {confirmDelete ? (
        <div className="confirm-overlay">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-account-title"
          >
            <p className="eyebrow">不可撤销</p>
            <h2 id="delete-account-title">确认申请注销账户？</h2>
            <p>提交后需要再次验证身份。完成删除后，关注与通知无法恢复。</p>
            <label>
              <span>输入“注销账户”继续</span>
              <input />
            </label>
            <div>
              <button
                className="button secondary"
                type="button"
                onClick={() => setConfirmDelete(false)}
              >
                取消
              </button>
              <button
                className="button danger"
                type="button"
                onClick={() => {
                  setConfirmDelete(false);
                  setMessage("注销申请已进入身份验证步骤");
                }}
              >
                继续验证
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}
