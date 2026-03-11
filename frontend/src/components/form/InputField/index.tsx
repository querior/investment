import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import { Typography, Input, Form, InputNumber } from 'antd';
import { FieldConfig, FieldInputProps, FieldMetaProps } from 'formik';

const types = ['password', 'text', 'email', 'number']

interface FormInputProps {
	name: string;
	type: string;
  label?: string;
  placeholder?: string;
  style?: React.CSSProperties
  prefix?: any;
	getFieldProps: (nameOrOptions: string | FieldConfig<any>) => FieldInputProps<any>;
	getFieldMeta: (name: string) => FieldMetaProps<any>;
  onChange?: (v: number | null) => void
  min?: number;
  max?: number;
  step?: number
  formatter?: (value: number | undefined) => string
  disabled?: boolean
  autoFocus?: boolean
}

const { Title, Text } = Typography


const FormInput = ({ 
  prefix, 
  label, 
  placeholder, 
  type, 
  name, 
  getFieldProps, 
  getFieldMeta, 
  onChange, 
  style,
  min,
  max,
  step,
  formatter,
  disabled,
  autoFocus
}: FormInputProps) => {
	const meta = getFieldMeta(name);
	const fieldProps = getFieldProps(name);

  
	return (
		<Form.Item>
			{label && <Text>{label}</Text>}
      {type === 'password' && 
        <Input.Password
          {...fieldProps}
          placeholder="input password"
          iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
          disabled={disabled}
        />
      }
      { (type === 'number') &&
        <InputNumber
          prefix={prefix}
          {...fieldProps}
          onChange={onChange}
          placeholder={placeholder}
          style={style}
          min={min}
          max={max}
          step={step}
          formatter={formatter}
          decimalSeparator=','
          disabled={disabled}
        />
      }
      { (type === 'text' || types.indexOf(type) === -1) &&
        <Input
          autoFocus={autoFocus}
          prefix={prefix}
          {...fieldProps}
          type={type}
          placeholder={placeholder}
          style={style}
          disabled={disabled}
        />
      }
			{meta.touched && meta.error && <Text className='error' style={{ color: 'red'}}>{meta.error}</Text>}
		</Form.Item>
	);
};

export default FormInput;
