import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tooltip } from "antd";
import { DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import type { RootState } from "../store/reducers";
import {
	fetchBacktestsRequest,
	createBacktestRequest,
	clearLastCreatedId,
	updateBacktestRequest,
	deleteBacktestRequest,
} from "../features/backtest/reducer";
import type { BacktestDto } from "../services/backtest-service";

type CreateFormValues = {
	name: string;
	description?: string;
	frequency: string;
};

type EditFormValues = {
	name: string;
	description?: string;
};

export default function Backtest() {
	const dispatch = useDispatch();
	const navigate = useNavigate();

	const { backtests, total, page, loading, creating, lastCreatedId } = useSelector(
		(state: RootState) => state.backtest
	);

	const [createModalOpen, setCreateModalOpen] = useState(false);
	const [editingBt, setEditingBt] = useState<BacktestDto | null>(null);
	const [createForm] = Form.useForm<CreateFormValues>();
	const [editForm] = Form.useForm<EditFormValues>();

	useEffect(() => {
		dispatch(clearLastCreatedId());
		dispatch(fetchBacktestsRequest());
	}, [dispatch]);

	useEffect(() => {
		if (lastCreatedId !== null) {
			setCreateModalOpen(false);
			createForm.resetFields();
			navigate(`/analysis/backtest/${lastCreatedId}`);
			dispatch(clearLastCreatedId());
		}
	}, [lastCreatedId, navigate, createForm, dispatch]);

	const handleCreate = async () => {
		const values = await createForm.validateFields();
		dispatch(createBacktestRequest({
			name: values.name,
			description: values.description,
			frequency: values.frequency,
		}));
	};

	const openEdit = (bt: BacktestDto) => {
		setEditingBt(bt);
		editForm.setFieldsValue({ name: bt.name, description: bt.description ?? undefined });
	};

	const handleEdit = async () => {
		if (!editingBt) return;
		const values = await editForm.validateFields();
		dispatch(updateBacktestRequest({ id: editingBt.id, ...values }));
		setEditingBt(null);
		editForm.resetFields();
	};

	const columns: ColumnsType<BacktestDto> = [
		{ title: "Name", dataIndex: "name", key: "name" },
		{
			title: "Description",
			dataIndex: "description",
			key: "description",
			render: (v: string | null) => v ?? "—",
		},
		{ title: "Frequency", dataIndex: "frequency", key: "frequency" },
		{ title: "Version", dataIndex: "strategy_version", key: "strategy_version" },
		{
			title: "Created at",
			dataIndex: "created_at",
			key: "created_at",
			render: (v: string) => new Date(v).toLocaleDateString("it-IT"),
		},
		{
			title: "Updated at",
			dataIndex: "updated_at",
			key: "updated_at",
			render: (v: string) => new Date(v).toLocaleDateString("it-IT"),
		},
		{
			title: "Actions",
			key: "actions",
			align: "center",
			render: (_: unknown, bt: BacktestDto) => (
				<Space>
					<Tooltip title="View">
						<Button
							type="text"
							icon={<EyeOutlined />}
							onClick={() => navigate(`/analysis/backtest/${bt.id}`)}
						/>
					</Tooltip>
					<Tooltip title="Edit">
						<Button
							type="text"
							icon={<EditOutlined />}
							onClick={() => openEdit(bt)}
						/>
					</Tooltip>
					<Tooltip title="Delete">
						<Popconfirm
							title="Delete this backtest?"
							okText="Delete"
							cancelText="Cancel"
							okButtonProps={{ danger: true }}
							onConfirm={() => dispatch(deleteBacktestRequest(bt.id))}
						>
							<Button type="text" danger icon={<DeleteOutlined />} />
						</Popconfirm>
					</Tooltip>
				</Space>
			),
		},
	];

	return (
		<div className="p-6">
			<div className="flex items-center justify-end mb-6">
				<Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
					Add
				</Button>
			</div>

			<Table
				rowKey="id"
				columns={columns}
				dataSource={backtests}
				loading={loading}
				pagination={{
					current: page,
					total,
					pageSize: 20,
					showTotal: (t) => `${t} backtests`,
					onChange: (p) => dispatch(fetchBacktestsRequest({ page: p })),
				}}
			/>

			{/* Create modal */}
			<Modal
				title="New backtest"
				open={createModalOpen}
				onOk={handleCreate}
				onCancel={() => setCreateModalOpen(false)}
				okText="Create"
				cancelText="Cancel"
				confirmLoading={creating}
				destroyOnHidden
			>
				<Form form={createForm} layout="vertical" className="mt-4" initialValues={{ frequency: "EOM" }}>
					<Form.Item name="name" label="Name" rules={[{ required: true, message: "Enter a name" }]}>
						<Input placeholder="e.g. Macro Allocation" />
					</Form.Item>
					<Form.Item name="description" label="Description">
						<Input.TextArea rows={2} placeholder="(optional)" />
					</Form.Item>
					<Form.Item name="frequency" label="Frequency" rules={[{ required: true }]}>
						<Select options={[
							{ value: "EOM", label: "End of Month (EOM)" },
							{ value: "EOW", label: "End of Week (EOW)" },
							{ value: "EOD", label: "End of Day (EOD)" },
						]} />
					</Form.Item>
				</Form>
			</Modal>

			{/* Edit modal */}
			<Modal
				title="Edit backtest"
				open={editingBt !== null}
				onOk={handleEdit}
				onCancel={() => { setEditingBt(null); editForm.resetFields(); }}
				okText="Save"
				cancelText="Cancel"
				destroyOnHidden
			>
				<Form form={editForm} layout="vertical" className="mt-4">
					<Form.Item name="name" label="Name" rules={[{ required: true, message: "Enter a name" }]}>
						<Input />
					</Form.Item>
					<Form.Item name="description" label="Description">
						<Input.TextArea rows={2} />
					</Form.Item>
				</Form>
			</Modal>
		</div>
	);
}
