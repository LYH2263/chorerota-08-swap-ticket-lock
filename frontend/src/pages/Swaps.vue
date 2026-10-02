<template>
  <div>
    <h1 class="brand">对调</h1>
    <p class="muted">对调台先发预演票：只校验并冻结票面四元组与双方成员，不改看板；持票确认才按票面成员交换两格</p>
    <div class="week-card" style="margin-bottom:12px">
      <label>A day <input type="number" v-model.number="form.a_day" /></label>
      <label>A task_id <input type="number" v-model.number="form.a_task" /></label>
      <label>B day <input type="number" v-model.number="form.b_day" /></label>
      <label>B task_id <input type="number" v-model.number="form.b_task" /></label>
      <button @click="preview">发预演票</button>
    </div>
    <p v-if="err" class="err">{{ err }}</p>
    <ul class="list">
      <li v-for="s in rows" :key="s.id">
        #{{ s.id }}
        D{{ s.a_day }}/T{{ s.a_task }} <b>{{ s.a_member_name || ('#'+s.a_member) }}</b>
        ↔ D{{ s.b_day }}/T{{ s.b_task }} <b>{{ s.b_member_name || ('#'+s.b_member) }}</b>
        <span class="chip" :class="chip(s.status)">{{ label(s.status) }}</span>
        <template v-if="s.status==='preview'">
          <button style="margin-left:8px" @click="confirm(s.id)">持票确认</button>
          <button class="ghost" @click="voidTicket(s.id)">作废</button>
        </template>
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
const err = ref('')
const form = ref({ a_day: 0, a_task: 1, b_day: 1, b_task: 1 })
function label(st) { return { preview: '预演', confirmed: '已确认', void: '已作废' }[st] || st }
function chip(st) { return { preview: 'coral', confirmed: '', void: 'ghost' }[st] || '' }
async function load() { rows.value = await api('/swaps') }
async function preview() {
  err.value = ''
  try {
    await api('/weeks/1/swaps', { method: 'POST', body: JSON.stringify(form.value) })
    await load()
  } catch (e) { err.value = e.message }
}
async function confirm(id) {
  err.value = ''
  try { await api('/swaps/' + id + '/confirm', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = '确认被拒：' + e.message + '（票面与现场不一致，格表未动）' ; await load() }
}
async function voidTicket(id) {
  err.value = ''
  try { await api('/swaps/' + id + '/void', { method: 'POST', body: '{}' }); await load() }
  catch (e) { err.value = e.message }
}
onMounted(load)
</script>
