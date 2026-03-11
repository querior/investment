import {
  Radio,
  Form,
  Typography,
  Flex,
  Divider
} from "antd";
import {
  FieldConfig,
  FieldInputProps,
  FieldMetaProps
} from "formik";

const { Text } = Typography

interface FormCheckboxProps {
  options: { value: string | number; label: string }[];
  defaultValue?: string | number;
  disabled: boolean;
  name: string;
  label?: string
  getFieldProps: (
    nameOrOptions: string | FieldConfig<any>
  ) => FieldInputProps<any>;
  getFieldMeta: (name: string) => FieldMetaProps<any>;
}


const RadioGroupField = ({
  options,
  defaultValue,
  disabled,
  name,
  label,
  getFieldProps,
  getFieldMeta,
}: FormCheckboxProps) => {
  const meta = getFieldMeta(name);
  const fieldProps = getFieldProps(name);  

  return (
    <Form.Item>
      <Flex vertical gap="middle">
      {label && <Text style={{ color: '#16255B', fontWeight: 600, textAlign: 'left'}} >{label}</Text>}
        <Radio.Group
          {...fieldProps}
          defaultValue={defaultValue}
          onChange={fieldProps.onChange}
          disabled={disabled}
          buttonStyle="solid"
        >
          {options.map((o,i) => (
            <Radio.Button  key={`opt-${i}`}  value={o.value} style={{ margin: 5, borderRadius:8}}>{o.label}</Radio.Button>
          ))}
        </Radio.Group>
        {meta.touched && meta.error && (
          <Text style={{ color: 'red'}} >
            {meta.error}
          </Text>
        )}
      </Flex>
    </Form.Item>
  );
};

export default RadioGroupField;
