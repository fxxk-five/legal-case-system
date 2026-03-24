import express from "express";
import puppeteer from "puppeteer-core";

const app = express();
app.use(express.json({ limit: "2mb" }));

const PORT = Number(process.env.PORT || 3001);
const executablePath = process.env.PUPPETEER_EXECUTABLE_PATH || "/usr/bin/chromium";

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function listItems(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "<li>无</li>";
  }
  return items.map((item) => `<li>${esc(item)}</li>`).join("");
}

function buildHtml(payload) {
  const caseInfo = payload.case || {};
  const timeline = Array.isArray(payload.timeline) ? payload.timeline : [];
  const files = Array.isArray(payload.files) ? payload.files : [];
  const analyses = Array.isArray(payload.analyses) ? payload.analyses : [];

  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>案件报告</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; font-size: 12px; color: #222; padding: 24px; }
    h1,h2 { margin: 8px 0; }
    .muted { color: #666; }
    table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
    th, td { border: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; }
    ul { margin: 6px 0 12px 18px; padding: 0; }
  </style>
</head>
<body>
  <h1>案件报告</h1>
  <p class="muted">生成时间：${esc(payload.generated_at)}</p>
  <p class="muted">角色：${esc(payload.role)}</p>

  <h2>案件概览</h2>
  <table>
    <tr><th>案号</th><td>${esc(caseInfo.case_number)}</td><th>标题</th><td>${esc(caseInfo.title)}</td></tr>
    <tr><th>案件状态</th><td>${esc(caseInfo.status)}</td><th>解析状态</th><td>${esc(caseInfo.analysis_status)} (${esc(caseInfo.analysis_progress)}%)</td></tr>
    <tr><th>当事人</th><td>${esc(caseInfo.client_name)}</td><th>律师</th><td>${esc(caseInfo.lawyer_name)}</td></tr>
    <tr><th>截止时间</th><td colspan="3">${esc(caseInfo.deadline || "")}</td></tr>
  </table>

  <h2>时间流</h2>
  <table>
    <tr><th>时间</th><th>事件</th><th>描述</th></tr>
    ${timeline
      .map(
        (item) => `<tr><td>${esc(item.occurred_at)}</td><td>${esc(item.title || item.event_type)}</td><td>${esc(item.description)}</td></tr>`,
      )
      .join("") || "<tr><td colspan='3'>暂无</td></tr>"}
  </table>

  <h2>证据材料</h2>
  <table>
    <tr><th>文件名</th><th>类型</th><th>解析状态</th><th>上传角色</th><th>描述</th></tr>
    ${files
      .map(
        (item) =>
          `<tr><td>${esc(item.file_name)}</td><td>${esc(item.file_type)}</td><td>${esc(item.parse_status)}</td><td>${esc(item.uploader_role)}</td><td>${esc(item.description)}</td></tr>`,
      )
      .join("") || "<tr><td colspan='5'>暂无</td></tr>"}
  </table>

  <h2>AI 分析摘要</h2>
  ${analyses
    .map(
      (item) => `
      <h3>${esc(item.analysis_type)}</h3>
      <p>${esc(item.summary)}</p>
      <p><strong>适用法条</strong></p>
      <ul>${listItems(item.applicable_laws)}</ul>
      <p><strong>优势</strong></p>
      <ul>${listItems(item.strengths)}</ul>
      <p><strong>不足</strong></p>
      <ul>${listItems(item.weaknesses)}</ul>
      <p><strong>建议</strong></p>
      <ul>${listItems(item.recommendations)}</ul>
    `,
    )
    .join("") || "<p>暂无分析结果。</p>"}
</body>
</html>`;
}

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.post("/api/v1/reports/render", async (req, res) => {
  let browser;
  try {
    const html = buildHtml(req.body || {});
    browser = await puppeteer.launch({
      executablePath,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
      headless: "new",
    });
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "networkidle0" });
    const pdf = await page.pdf({
      format: "A4",
      printBackground: true,
      margin: { top: "12mm", bottom: "12mm", left: "10mm", right: "10mm" },
    });
    const pdfBuffer = Buffer.isBuffer(pdf) ? pdf : Buffer.from(pdf);
    await browser.close();
    browser = null;
    res.setHeader("Content-Type", "application/pdf");
    res.send(pdfBuffer);
  } catch (error) {
    if (browser) {
      try {
        await browser.close();
      } catch {
        // Ignore close error.
      }
    }
    res.status(500).json({ message: "report_render_failed", detail: String(error?.message || error) });
  }
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`report-service listening on ${PORT}`);
});
