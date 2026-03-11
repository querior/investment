import { Typography, Form, Input } from 'antd';

import { FieldConfig, FieldInputProps, FieldMetaProps } from 'formik';

const { TextArea } = Input

interface FormInputProps {
	name: string;
  label?: string;
  placeholder?: string;
  style?: React.CSSProperties
  prefix?: any;
	getFieldProps: (nameOrOptions: string | FieldConfig<any>) => FieldInputProps<any>;
	getFieldMeta: (name: string) => FieldMetaProps<any>;
  disabled?: boolean;
}

const { Text } = Typography


const FormInput = ({ 
  prefix, 
  label, 
  placeholder,   
  name, 
  getFieldProps, 
  getFieldMeta,   
  style,
  disabled
}: FormInputProps) => {
	const meta = getFieldMeta(name);
	const fieldProps = getFieldProps(name);
  
	return (
		<Form.Item>
			{label && <Text>{label}</Text>}
      <TextArea
        prefix={prefix}
        {...fieldProps}
        placeholder={placeholder}
        style={style}
        rows={4}
        disabled={disabled}
      />
			{meta.touched && meta.error && <Text style={{ color: 'red'}}>{meta.error}</Text>}
		</Form.Item>
	);
};

export default FormInput;
