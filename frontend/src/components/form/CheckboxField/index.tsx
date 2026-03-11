import {
  Button,
  Checkbox,
  CheckboxProps,
  Form,
  Tooltip,
  Typography,
} from "antd";
import {
  FieldConfig,
  FieldInputProps,
  FieldMetaProps
} from "formik";

const { Text } = Typography

interface FormCheckboxProps {
  label: string;
  name: string;
  getFieldProps: (
    nameOrOptions: string | FieldConfig<any>
  ) => FieldInputProps<any>;
  getFieldMeta: (name: string) => FieldMetaProps<any>;
  onChange: CheckboxProps['onChange'] 
  style?: React.CSSProperties
  tooltip?: string;
}

const CheckboxField = ({
  label,
  name,
  style,
  tooltip,
  getFieldProps,
  getFieldMeta,
  onChange
}: FormCheckboxProps) => {
  const meta = getFieldMeta(name);
  const fieldProps = getFieldProps(name);  

  return (
		<Form.Item>
			<Checkbox {...fieldProps} checked={fieldProps.value} onChange={onChange} style={style}>
        { tooltip &&
          <Tooltip title={tooltip} color="black">
            {/* <Button style={tooltipButtonCss} block >{tooltip}</Button> */}
            {label}
          </Tooltip>
        }
        {
          !tooltip && <p>{label}</p>
        }
				
			</Checkbox>
			{meta.touched && meta.error && (
				<Text style={{ color: "red" }}>{meta.error}</Text>
			)}
		</Form.Item>
	);
};

const tooltipButtonCss: React.CSSProperties = { 
  background: '#16255B', 
  color: 'white', 
  border: 0, 
  fontSize: 12, 
  fontWeight: 'bold'
}

export default CheckboxField;
