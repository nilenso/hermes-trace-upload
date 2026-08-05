import { host, ROUTES_AREA, SIDEBAR_NAV_AREA, PALETTE_AREA, useQuery, useMutation, useQueryClient, Button, Input } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const key = ['traces', 'config']
const fieldClass = 'w-full rounded border border-(--ui-stroke-secondary) bg-transparent px-2 py-1 text-sm text-(--ui-text-primary)'

function TracesSettings({ ctx }) {
  const queryClient = useQueryClient()
  const configQuery = useQuery({ queryKey: key, queryFn: () => ctx.rest('/config') })
  const save = useMutation({
    mutationFn: body => ctx.rest('/config', { method: 'PUT', body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
    onError: error => host.notifyError(error, 'Could not save Traces settings')
  })
  const upload = useMutation({
    mutationFn: body => ctx.rest('/upload', { method: 'POST', body }),
    onSuccess: result => host.notify({ kind: 'success', message: `Trace ${result.action}: ${result.trace_id}` }),
    onError: error => host.notifyError(error, 'Trace upload failed')
  })
  if (configQuery.isLoading) return jsx('div', { className: 'p-4 text-sm text-(--ui-text-tertiary)', children: 'Loading Traces settings…' })
  const data = configQuery.data || { config: { provider: 'traces.com-cli', cli_path: 'traces', namespace: '', visibility: 'private' } }
  const config = data.config
  const submit = event => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    save.mutate({ provider: form.get('provider'), cli_path: form.get('cli_path'), namespace: form.get('namespace'), visibility: form.get('visibility') })
  }
  const uploadActive = () => upload.mutate({ cwd: host.state.cwd.get(), trace_id: host.state.activeSessionId.get() || null })
  return jsxs('div', { className: 'h-full overflow-auto p-5 text-sm', children: [
    jsx('h1', { className: 'mb-1 text-lg font-semibold', children: 'Traces' }),
    jsx('p', { className: 'mb-5 text-(--ui-text-tertiary)', children: 'Configure the trace host and upload the active Hermes session.' }),
    jsx('form', { className: 'max-w-xl space-y-4', onSubmit: submit, children: jsxs('div', { className: 'space-y-4', children: [
      jsxs('label', { className: 'block space-y-1', children: [jsx('span', { className: 'font-medium', children: 'Trace provider' }), jsx('select', { name: 'provider', defaultValue: config.provider, className: fieldClass, children: jsx('option', { value: 'traces.com-cli', children: 'traces.com CLI' }) })] }),
      jsxs('label', { className: 'block space-y-1', children: [jsx('span', { className: 'font-medium', children: 'Traces CLI executable' }), jsx(Input, { name: 'cli_path', defaultValue: config.cli_path, placeholder: 'traces' }), jsx('span', { className: 'text-xs text-(--ui-text-tertiary)', children: data.status?.resolved_cli ? `Resolved: ${data.status.resolved_cli}` : (data.status_error || 'Must be available on the gateway PATH.') })] }),
      jsxs('label', { className: 'block space-y-1', children: [jsx('span', { className: 'font-medium', children: 'Namespace (optional)' }), jsx(Input, { name: 'namespace', defaultValue: config.namespace, placeholder: 'Uses the active Traces CLI namespace' })] }),
      jsxs('label', { className: 'block space-y-1', children: [jsx('span', { className: 'font-medium', children: 'Visibility' }), jsx('select', { name: 'visibility', defaultValue: config.visibility, className: fieldClass, children: [jsx('option', { value: 'private', children: 'Private' }), jsx('option', { value: 'direct', children: 'Direct link' }), jsx('option', { value: 'public', children: 'Public' })] })] }),
      jsx(Button, { type: 'submit', disabled: save.isPending, children: save.isPending ? 'Saving…' : 'Save settings' })
    ] }) }),
    jsx('div', { className: 'mt-8 border-t border-(--ui-stroke-secondary) pt-5', children: jsxs('div', { className: 'space-y-2', children: [jsx('div', { className: 'font-medium', children: 'Active trace' }), jsx('p', { className: 'text-(--ui-text-tertiary)', children: 'Uses the active Hermes session ID. Re-running refreshes the same remote trace.' }), jsx(Button, { onClick: uploadActive, disabled: upload.isPending, children: upload.isPending ? 'Uploading…' : 'Upload active trace' })] }) })
  ] })
}

export default {
  id: 'traces', name: 'Traces', defaultEnabled: true,
  register(ctx) {
    ctx.registerMany([
      { id: 'page', area: ROUTES_AREA, data: { path: '/traces' }, render: () => jsx(TracesSettings, { ctx }) },
      { id: 'nav', area: SIDEBAR_NAV_AREA, data: { path: '/traces', label: 'Traces', codicon: 'pulse' } },
      { id: 'open', area: PALETTE_AREA, data: { id: 'traces.open', label: 'Open Traces settings', keywords: ['trace', 'upload', 'observability'], run: () => host.navigate('/traces') } }
    ])
  }
}
