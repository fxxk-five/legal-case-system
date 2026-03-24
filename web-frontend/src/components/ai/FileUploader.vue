<template>
  <div class="space-y-6">
    <el-upload
      :http-request="handleUploadRequest"
      :on-success="handleSuccess"
      :on-error="handleError"
      :before-upload="beforeUpload"
      :file-list="fileList"
      drag
      multiple
      class="apple-upload"
    >
      <div class="flex flex-col items-center justify-center py-10">
        <div class="mb-5 flex h-20 w-20 items-center justify-center rounded-full bg-blue-50 transition-transform duration-300 group-hover:scale-110">
          <UploadCloudIcon class="h-10 w-10 text-[#007AFF]" />
        </div>
        <div class="mb-2 text-base font-semibold text-gray-800">
          Drop files here or <span class="text-[#007AFF] hover:opacity-80">click to upload</span>
        </div>
        <div class="text-sm text-gray-400">
          Supports PDF, Word, images and spreadsheets. Max 50MB per file.
        </div>
      </div>
    </el-upload>

    <div v-if="uploadedFiles.length > 0" class="space-y-4">
      <h4 class="px-1 text-xs font-bold uppercase tracking-widest text-gray-400">Uploaded Files</h4>
      <div class="grid grid-cols-1 gap-3">
        <div
          v-for="file in uploadedFiles"
          :key="file.id"
          class="flex items-center justify-between rounded-2xl border border-gray-100 bg-white p-4 shadow-sm transition-all duration-300 hover:shadow-md"
        >
          <div class="flex min-w-0 items-center gap-4">
            <div class="rounded-xl bg-gray-50 p-2.5">
              <FileIcon class="h-6 w-6 shrink-0 text-gray-400" />
            </div>
            <div class="min-w-0">
              <p class="truncate text-sm font-semibold text-gray-800">{{ file.file_name }}</p>
              <p class="text-[10px] font-bold uppercase tracking-tight text-gray-400">{{ file.file_type }}</p>
            </div>
          </div>
          <button
            class="apple-btn-primary !px-5 !py-2 !text-xs"
            @click="$emit('parse', file.id)"
          >
            Start Parse
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { UploadCloudIcon, FileIcon } from 'lucide-vue-next'

import { uploadCaseFileByPolicy } from '@/lib/fileUpload'
import { extractFriendlyError } from '@/lib/formMessages'

const props = defineProps({
  caseId: {
    type: Number,
    required: true,
  },
})

const emit = defineEmits(['success', 'parse'])

const fileList = ref([])
const uploadedFiles = ref([])

const beforeUpload = (file) => {
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('File size cannot exceed 50MB.')
    return false
  }

  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'image/jpeg',
    'image/png',
    'image/jpg',
    'text/plain',
  ]

  if (file.type && !allowedTypes.includes(file.type)) {
    ElMessage.error('Unsupported file format.')
    return false
  }

  return true
}

const handleUploadRequest = async (options) => {
  try {
    const uploaded = await uploadCaseFileByPolicy(props.caseId, options.file, {
      onProgress: options.onProgress,
    })
    options.onSuccess?.(uploaded)
  } catch (error) {
    options.onError?.(error)
  }
}

const handleSuccess = (response) => {
  uploadedFiles.value.push(response)
  emit('success', response)
}

const parseUploadPayload = (message) => {
  if (typeof message !== 'string' || !message.trim()) {
    return null
  }

  try {
    const parsed = JSON.parse(message)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

const extractUploadErrorMessage = (error) => {
  if (typeof error?.message === 'string' && error.message.trim()) {
    const payload = parseUploadPayload(error.message)
    if (payload?.message) {
      return payload.message
    }
    return error.message.trim()
  }

  return extractFriendlyError(error, 'File upload failed.')
}

const handleError = (error) => {
  ElMessage.error(extractUploadErrorMessage(error))
}
</script>

<style>
.apple-upload .el-upload-dragger {
  @apply !bg-gray-50/50 !border-2 !border-dashed !border-gray-200 !rounded-[2rem] hover:!border-[#007AFF] hover:!bg-blue-50/30 transition-all duration-500;
}
.apple-upload .el-upload-list__item {
  @apply !rounded-2xl !border !border-gray-100 !bg-white !shadow-sm;
}
</style>
