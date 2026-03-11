import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { Typography, Input, Form, DatePicker } from 'antd';
import { FieldConfig, FieldInputProps, FieldMetaProps } from 'formik';
import { useState } from 'react';

interface FormInputProps {
	name: string;
	picker?: "month" | "week" | "year" | "quarter";
  label?: string;
  placeholder?: string;
  prefix?: any;
	getFieldProps: (nameOrOptions: string | FieldConfig<any>) => FieldInputProps<any>;
	getFieldMeta: (name: string) => FieldMetaProps<any>;
	onChange: any
}

const { Title, Text } = Typography


const FormDatePicker = ({ prefix, label, placeholder, name, picker, onChange, getFieldProps, getFieldMeta, ...props }: FormInputProps) => {
	const meta = getFieldMeta(name);
	const fieldProps = getFieldProps(name);

	return (
		<Form.Item>
			{label && <Title level={5}>{label}</Title>}
      <DatePicker 
        {...fieldProps}
        picker={picker}
        name={name}    
				onChange={onChange}
				onBlur={() => null}
      />      
			{meta.touched && meta.error && <Text color='red'>{meta.error}</Text>}
		</Form.Item>
	);
};

export default FormDatePicker;
