import { DatePicker, Form, FormInstance, Input, Modal, Select } from "antd";
import type { Dayjs } from "dayjs";
import {
	FrequencyType,
	INITIAL_ALLOCATION_OPTIONS,
	InitialAllocation,
} from "../../features/backtest/types";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "../../store/reducers";
import { createRunRequest } from "../../features/backtest/reducer";

type AddRunFormValues = {
	name?: string;
	range: [Dayjs, Dayjs];
	notes?: string;
	initial_allocation?: InitialAllocation;
};

interface AddBacktestRunModalProps {
	backtestId: number;
	addRunOpen: boolean;
	setAddRunOpen: (open: boolean) => void;
}

const AddBacktestRunModal = ({
	backtestId,
	addRunOpen,
	setAddRunOpen,
}: AddBacktestRunModalProps) => {
	const dispatch = useDispatch();
	const { current, creatingRun } = useSelector(
		(state: RootState) => state.backtest
	);
	const [addRunForm] = Form.useForm<AddRunFormValues>();

	const handleAddRun = async () => {
		const values = await addRunForm.validateFields();
		dispatch(
			createRunRequest({
				backtestId,
				payload: {
					name: values.name || undefined,
					start: values.range[0].format("YYYY-MM-DD"),
					end: values.range[1].format("YYYY-MM-DD"),
					notes: values.notes,
					initial_allocation:
						current?.frequency === "EOM"
							? values.initial_allocation
							: undefined,
				},
			})
		);
		setAddRunOpen(false);
		addRunForm.resetFields();
	};

	return (
		<Modal
			title="New run"
			open={addRunOpen}
			onOk={handleAddRun}
			onCancel={() => {
				setAddRunOpen(false);
				addRunForm.resetFields();
			}}
			okText="Create"
			cancelText="Cancel"
			confirmLoading={creatingRun}
			destroyOnHidden
		>
			<Form
				form={addRunForm}
				layout="vertical"
				className="mt-4"
				initialValues={{ initial_allocation: "neutral" }}
			>
				<Form.Item name="name" label="Name">
					<Input placeholder="e.g. M0 baseline" />
				</Form.Item>
				<Form.Item
					name="range"
					label="Period"
					rules={[{ required: true, message: "Select a period" }]}
				>
					<DatePicker.RangePicker
						picker="month"
						style={{ width: "100%" }}
						format="YYYY-MM"
					/>
				</Form.Item>
				{current?.frequency === FrequencyType.EOM && (
					<Form.Item
						name="initial_allocation"
						label="Starting allocation"
						rules={[{ required: true }]}
					>
						<Select options={INITIAL_ALLOCATION_OPTIONS} />
					</Form.Item>
				)}
				<Form.Item name="notes" label="Notes">
					<Input.TextArea rows={2} placeholder="(optional)" />
				</Form.Item>
			</Form>
		</Modal>
	);
};

export default AddBacktestRunModal;
