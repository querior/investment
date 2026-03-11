import {
  Select,
  Form,
  Typography,
} from "antd";
import {
  FieldConfig,
  FieldInputProps,
  FieldMetaProps,
  FormikErrors
} from "formik";
import React from "react";

const { Text } = Typography

interface FormSelectProps {
  options: { value: string | number; label: string }[];
  defaultValue?: string | number;
  disabled: boolean;
  name: string;
  label?: string
  placeholder?: string
  getFieldProps: (
    nameOrOptions: string | FieldConfig<any>
  ) => FieldInputProps<any>;
  getFieldMeta: (name: string) => FieldMetaProps<any>;
  setFieldValue: (
    field: string,
    value: any,
    shouldValidate?: boolean | undefined,
  ) => Promise<void> | Promise<FormikErrors<any>>;
  onChange?: (v: any) => void
  style?: React.CSSProperties
}


const SelectField = ({
  options,
  defaultValue,
  disabled,
  name,
  label,
  placeholder,
  getFieldProps,
  getFieldMeta,
  setFieldValue,
  onChange,
  style
}: FormSelectProps) => {
  const meta = getFieldMeta(name);
  const fieldProps = getFieldProps(name);  
  
  const handleChange = (e: any) => {
    setFieldValue(fieldProps.name, e);
  };

  return (
    <Form.Item>     
        {label && <Text>{label}</Text>}
        <Select
          {...fieldProps}
          defaultValue={defaultValue}
          disabled={disabled}
          options={options}
          onChange={onChange || handleChange}
          placeholder={placeholder}
          style={style}
        />
        {meta.touched && meta.error && (
          <Text style={{ color: 'red'}}>
            {meta.error}
          </Text>
      )}  
    </Form.Item>
  );
};

export default SelectField;
