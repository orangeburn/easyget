const API_BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

type RequestOptions = RequestInit & { expectText?: boolean };

async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const detail = errorData.detail || errorData.message;
      throw new Error(detail || `请求失败 (${response.status})`);
    }
    if (options?.expectText) {
      return (await response.text()) as T;
    }
    return response.json();
  } catch (error: any) {
    // Network errors in browsers surface as TypeError; add actionable hint.
    if (error instanceof TypeError) {
      throw new Error('无法连接后端服务，请确认后端已启动 (http://127.0.0.1:8000)');
    }
    throw error;
  }
}

export const apiService = {
  async parseInitialDocument(text: string) {
    return request('/parser/initial', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
  },

  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return request('/parser/upload', {
      method: 'POST',
      body: formData
    });
  },

  async generateDynamicForm(constraint: any) {
    const data = await request('/parser/form', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(constraint)
    });
    // 映射后端字段到前端组件预期的字段
    return {
      industry_type: data.industry_type,
      items: (data.form_items || []).map((item: any) => ({
        field_id: item.field_id,
        label: item.label,
        type: item.field_type,
        options: item.options,
        placeholder: item.placeholder,
        required: item.is_required
      }))
    };
  },

  async updateConstraint(constraint: any, formData: any) {
    return request('/parser/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ constraint, form_data: formData })
    });
  },

  async generateKeywords(constraint: any) {
    return request('/parser/keywords', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(constraint)
    });
  },

  async activateTask(constraint: any, strategy: any) {
    return request('/task/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ constraint, strategy })
    });
  },

  async getClues() {
    return request('/clues');
  },

  async getSystemState() {
    return request('/state');
  },

  async updateClueFeedback(clueId: string, feedback: number) {
    return request(`/clues/${clueId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback })
    });
  },

  async exportClues() {
    window.open(`${API_BASE_URL}/clues/export`, '_blank');
  }
};
