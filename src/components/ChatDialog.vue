<template>
  <el-card class="chat-card" shadow="hover">
    <div slot="header" class="chat-header">
      <span class="chat-title">{{ title }}</span>
      <el-button type="text" class="chat-clear" @click="resetConversation">清空</el-button>
    </div>

    <el-scrollbar ref="scrollbar" class="chat-scrollbar">
      <div class="chat-list">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="chat-row"
          :class="`role-${msg.role}`"
        >
          <div class="chat-bubble">
            <div v-if="msg.content" class="chat-text">{{ msg.content }}</div>
            <div v-else-if="msg.pending" class="chat-text pending-text">处理中...</div>

            <div v-if="msg.role === 'assistant' && msg.steps.length" class="step-card-list">
              <el-card v-for="(step, idx) in msg.steps" :key="step.id" shadow="never" class="step-card" :class="`step-${step.type}`">
                <div slot="header" class="step-card-header">step{{ idx + 1 }}</div>
                <div class="step-card-body">
                  <div class="step-card-text">{{ step.text }}</div>
                  <div class="step-card-time">{{ step.time }}</div>
                </div>
              </el-card>
            </div>
          </div>
        </div>
      </div>
    </el-scrollbar>

    <div class="chat-input">
      <el-input
        v-model.trim="draft"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="placeholder"
        @keyup.enter.native="onEnter"
      ></el-input>
      <el-button type="primary" class="send-btn" icon="el-icon-s-promotion" circle :loading="sending" @click="sendMessage"></el-button>
    </div>
  </el-card>
</template>

<script>
export default {
  name: 'ChatDialog',
  props: {
    title: {
      type: String,
      default: '运维助手对话'
    },
    placeholder: {
      type: String,
      default: '请输入问题，按 Enter 发送，Shift + Enter 换行'
    }
  },
  data() {
    return {
      draft: '',
      sending: false,
      seq: 0,
      messages: [
        {
          id: 'msg-assistant-welcome',
          role: 'assistant',
          content: '你好，我可以帮你分析链路、定位异常并展示每一步处理过程。',
          steps: []
        }
      ]
    }
  },
  methods: {
    onEnter(event) {
      if (event.shiftKey) return
      event.preventDefault()
      this.sendMessage()
    },
    sendMessage() {
      const text = (this.draft || '').trim()
      if (!text || this.sending) return

      const userId = this.genId('user')
      const assistantId = this.genId('assistant')

      this.messages.push({
        id: userId,
        role: 'user',
        content: text,
        steps: []
      })

      this.messages.push({
        id: assistantId,
        role: 'assistant',
        content: '',
        pending: true,
        steps: []
      })

      this.draft = ''
      this.sending = true
      this.scrollToBottom()

      this.$emit('send', {
        text,
        assistantMessageId: assistantId
      })
    },

    appendAssistantStep(messageId, stepText, stepType = 'primary') {
      const message = this.findMessage(messageId)
      if (!message || message.role !== 'assistant') return
      message.steps.push({
        id: this.genId('step'),
        text: stepText,
        type: stepType,
        time: this.formatTime()
      })
      this.scrollToBottom()
    },

    finishAssistantReply(messageId, content) {
      const message = this.findMessage(messageId)
      if (!message || message.role !== 'assistant') return
      message.content = content
      message.pending = false
      this.sending = false
      this.scrollToBottom()
    },

    failAssistantReply(messageId, errorText) {
      const message = this.findMessage(messageId)
      if (!message || message.role !== 'assistant') return
      message.content = errorText || '处理失败，请稍后重试。'
      message.pending = false
      this.sending = false
      this.appendAssistantStep(messageId, '处理失败', 'danger')
      this.scrollToBottom()
    },

    resetConversation() {
      this.messages = [
        {
          id: 'msg-assistant-welcome',
          role: 'assistant',
          content: '你好，我可以帮你分析链路、定位异常并展示每一步处理过程。',
          steps: []
        }
      ]
      this.draft = ''
      this.sending = false
      this.scrollToBottom()
    },

    findMessage(id) {
      return this.messages.find((item) => item.id === id)
    },
    genId(prefix) {
      this.seq += 1
      return `${prefix}-${Date.now()}-${this.seq}`
    },
    formatTime() {
      const now = new Date()
      const pad = (n) => String(n).padStart(2, '0')
      return `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const scrollbar = this.$refs.scrollbar
        const wrap = scrollbar && scrollbar.$refs && scrollbar.$refs.wrap
        if (wrap) wrap.scrollTop = wrap.scrollHeight
      })
    }
  }
}
</script>

<style scoped>
.chat-card {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-card /deep/ .el-card__header {
  padding: 10px 12px;
}

.chat-card /deep/ .el-card__body {
  flex: 1;
  padding: 12px;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-title {
  font-size: 13px;
  font-weight: 600;
  color: #2d3a4a;
}

.chat-clear {
  padding: 0;
  line-height: 1;
}

.chat-scrollbar {
  flex: 1;
  min-height: 0;
}

.chat-list {
  padding-right: 6px;
}

.chat-row {
  display: flex;
  margin-bottom: 10px;
}

.role-user {
  justify-content: flex-end;
}

.role-assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: 92%;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.55;
  word-break: break-word;
  white-space: pre-wrap;
}

.role-user .chat-bubble {
  background: #e6f1ff;
  border: 1px solid #b8d6ff;
  color: #1f2d3d;
}

.role-assistant .chat-bubble {
  background: #f7f9fc;
  border: 1px solid #e1e8f3;
  color: #2d3a4a;
}

.pending-text {
  color: #5d6b86;
}

.step-card-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.step-card {
  border: 1px solid #d6e4f7;
}

.step-card /deep/ .el-card__header {
  padding: 6px 10px;
  background: #f3f8ff;
  font-size: 12px;
  font-weight: 600;
  color: #2d4e78;
}

.step-card /deep/ .el-card__body {
  padding: 8px 10px;
}

.step-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-card-text {
  color: #2d3a4a;
}

.step-card-time {
  color: #8090aa;
  font-size: 11px;
}

.step-success {
  border-color: #b7e9d4;
}

.step-success /deep/ .el-card__header {
  background: #effaf4;
  color: #2a7f5f;
}

.step-danger {
  border-color: #f7c2c2;
}

.step-danger /deep/ .el-card__header {
  background: #fff3f3;
  color: #b64545;
}

.chat-input {
  border-top: 1px solid #e4ebf5;
  margin-top: 10px;
  padding-top: 10px;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input /deep/ .el-textarea__inner {
  font-size: 12px;
}

.send-btn {
  flex-shrink: 0;
}
</style>
