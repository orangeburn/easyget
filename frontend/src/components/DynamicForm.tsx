import React from 'react';

interface FormItem {
  field_id: string;
  label: string;
  type: 'text' | 'select' | 'multiselect' | 'boolean';
  options?: string[];
  placeholder?: string;
  required: boolean;
}

interface DynamicFormProps {
  schema: {
    items: FormItem[];
  };
  values: Record<string, any>;
  onChange: (field: string, value: any) => void;
}

export const DynamicForm: React.FC<DynamicFormProps> = ({ schema, values, onChange }) => {
  return (
    <div className="dynamic-form">
      {schema?.items?.map((item) => {
        const fieldType = item.type || (item as any).field_type;
        const isBoolean = fieldType === 'boolean';
        return (
          <div key={item.field_id} className={`form-item ${isBoolean ? 'form-item-boolean' : ''}`}>
            <label className="form-label">
              {item.label}
              {item.required && <span className="required-star">*</span>}
            </label>
            
            {fieldType === 'text' && (
              <input
                type="text"
                className="form-input"
                placeholder={item.placeholder}
                value={values[item.field_id] || ''}
                onChange={(e) => onChange(item.field_id, e.target.value)}
              />
            )}

            {fieldType === 'boolean' && (
              <div className="toggle-box">
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={!!values[item.field_id]}
                    onChange={(e) => onChange(item.field_id, e.target.checked)}
                  />
                  <span className="slider round"></span>
                </label>
                <span className="toggle-text">{values[item.field_id] ? '是' : '否'}</span>
              </div>
            )}

            {(fieldType === 'select' || fieldType === 'multiselect') && (
              <div className="select-box">
                <select
                  className="form-select"
                  value={values[item.field_id] || ''}
                  onChange={(e) => onChange(item.field_id, e.target.value)}
                >
                  <option value="" disabled>请选择...</option>
                  {item.options?.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
