import { Form, FormInstance, Input, Modal, Select } from "antd";
import { RootState } from "../../store/reducers";
import { useDispatch, useSelector } from "react-redux";
import {
	createBacktestRequest,
	updateBacktestRequest,
} from "../../features/backtest/reducer";
import {
	BacktestDto,
	FrequencyType,
	Instrument,
} from "../../features/backtest/types";
import { useEffect } from "react";

export type CreateFormValues = {
	name: string;
	description?: string;
	frequency: string;
	instrument?: Instrument;
};

interface UpsertBacktestModalProps {
	backtest: BacktestDto | null;
	open: boolean;
	setOpen: (value: boolean) => void;
	upsertForm: FormInstance<CreateFormValues>;
	setBacktest: (bt: BacktestDto | null) => void;
}

const UpsertBacktestModal = ({
	backtest,
	open,
	setOpen,
	upsertForm,
	setBacktest,
}: UpsertBacktestModalProps) => {
	const dispatch = useDispatch();
	const { creating } = useSelector((state: RootState) => state.backtest);

	const frequency = Form.useWatch("frequency", upsertForm);

	const handleCreate = async () => {
		const values = await upsertForm.validateFields();
		if (!backtest) {
			dispatch(
				createBacktestRequest({
					name: values.name,
					description: values.description,
					frequency: values.frequency,
					instrument: values.instrument,
				})
			);
		} else {
			dispatch(updateBacktestRequest({ id: backtest.id, ...values }));
		}
		setBacktest(null);
		upsertForm.resetFields();
		setOpen(false);
	};

	useEffect(() => {
		if (backtest) {
			upsertForm.setFieldsValue({
				name: backtest.name,
				description: backtest.description ?? undefined,
			});
		} else {
			upsertForm.setFieldsValue({
				name: undefined,
				description: undefined,
				frequency: undefined,
				instrument: undefined,
			});
		}
	}, [backtest]);

	return (
		<Modal
			title={`${backtest ? "Edit" : "New"} backtest`}
			open={open}
			onOk={handleCreate}
			onCancel={() => setOpen(false)}
			okText={backtest ? "Update" : "Create"}
			cancelText="Cancel"
			confirmLoading={creating}
			destroyOnHidden
		>
			<Form
				form={upsertForm}
				layout="vertical"
				className="mt-4"
				initialValues={{ frequency: "EOM" }}
			>
				<Form.Item
					name="name"
					label="Name"
					rules={[{ required: true, message: "Enter a name" }]}
				>
					<Input placeholder="e.g. Macro Allocation" />
				</Form.Item>
				<Form.Item name="description" label="Description">
					<Input.TextArea rows={2} placeholder="(optional)" />
				</Form.Item>
				{!backtest && (
					<Form.Item
						name="frequency"
						label="Frequency"
						rules={[{ required: true }]}
					>
						<Select
							options={[
								{ value: "EOM", label: "End of Month (EOM)" },
								{ value: "EOW", label: "End of Week (EOW)" },
								{ value: "EOD", label: "End of Day (EOD)" },
							]}
						/>
					</Form.Item>
				)}
				{!backtest &&
					(frequency === FrequencyType.EOD ||
						frequency === FrequencyType.EOW) && (
						<Form.Item name="instrument" label="Instrument">
							<Select
								options={[
									{ value: "options", label: "Options" },
									{ value: "futures", label: "Futures" },
								]}
							/>
						</Form.Item>
					)}
			</Form>
		</Modal>
	);
};

export default UpsertBacktestModal;
