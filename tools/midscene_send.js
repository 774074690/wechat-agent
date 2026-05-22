/**
 * midscene_send.js — 用 Midscene 视觉 AI 在手机上发微信
 * 用法: node midscene_send.js "联系人" "消息内容"
 *
 * AI 配置通过环境变量:
 *   MIDSCENE_MODEL_BASE_URL, MIDSCENE_MODEL_API_KEY
 *   MIDSCENE_MODEL_NAME, MIDSCENE_MODEL_FAMILY
 *   MIDSCENE_MODEL_REASONING_ENABLED
 */
const { agentFromAdbDevice } = require('@midscene/android');
const { execSync } = require('child_process');

const DEVICE_ID = '396f99ce';

function waitForDevice(maxWait = 20) {
  for (let i = 0; i < maxWait; i++) {
    const out = execSync('adb devices', { encoding: 'utf8', timeout: 5000 });
    for (const line of out.split('\n')) {
      if (line.includes(DEVICE_ID) && line.includes('device') && !line.includes('offline')) {
        return true;
      }
    }
    execSync('adb reconnect', { encoding: 'utf8', timeout: 5000, stdio: 'ignore' });
    execSync('sleep 2', { stdio: 'ignore' });
  }
  return false;
}

async function main(contact, message) {
  console.log(`📱 等待设备连接...`);
  if (!waitForDevice()) throw new Error('设备连接不上');

  console.log(`📤 连接 Midscene...`);
  const agent = await agentFromAdbDevice(DEVICE_ID);

  console.log(`📤 打开微信搜 ${contact}...`);
  await agent.aiAction(
    `Open WeChat on the phone, tap the search bar at the top, search for contact "${contact}", ` +
    `open their chat, type the message "${message}" in the input box, then press send.`,
    { deepThink: false }
  );

  console.log(`✅ 发送完成`);
  process.exit(0);
}

const [contact, message] = process.argv.slice(2);
if (!contact || !message) {
  console.log('用法: node midscene_send.js "联系人" "消息内容"');
  process.exit(1);
}

main(contact, message).catch(e => {
  console.error('❌ 失败:', e.message);
  process.exit(1);
});
