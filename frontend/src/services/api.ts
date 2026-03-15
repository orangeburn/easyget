const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const apiService = {
  async parseInitialDocument(text: string) {
    const response = await fetch(`${API_BASE_URL}/parser/initial`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to parse document');
    }
    return response.json();
  },

  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/parser/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Failed to upload document');
    return response.json();
  },

  async generateDynamicForm(constraint: any) {
    const response = await fetch(`${API_BASE_URL}/parser/form`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(constraint),
    });
    if (!response.ok) throw new Error('Failed to generate form');
    const data = await response.json();
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
    const response = await fetch(`${API_BASE_URL}/parser/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ constraint, form_data: formData }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Failed to update constraint');
    }
    return response.json();
  },

  async generateKeywords(constraint: any) {
    const response = await fetch(`${API_BASE_URL}/parser/keywords`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(constraint),
    });
    if (!response.ok) throw new Error('Failed to generate keywords');
    return response.json();
  },

  async activateTask(constraint: any, strategy: any) {
    const response = await fetch(`${API_BASE_URL}/task/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ constraint, strategy }),
    });
    if (!response.ok) throw new Error('Failed to activate task');
    return response.json();
  },

  async getClues() {
    const response = await fetch(`${API_BASE_URL}/clues`);
    if (!response.ok) throw new Error('Failed to fetch clues');
    return response.json();
  },

  async getSystemState() {
    const response = await fetch(`${API_BASE_URL}/state`);
    if (!response.ok) throw new Error('Failed to fetch state');
    return response.json();
  },

  async updateClueFeedback(clueId: string, feedback: number) {
    const response = await fetch(`${API_BASE_URL}/clues/${clueId}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feedback }),
    });
    if (!response.ok) throw new Error('Failed to update feedback');
    return response.json();
  },

  async exportClues() {
    window.open(`${API_BASE_URL}/clues/export`, '_blank');
  }
};
