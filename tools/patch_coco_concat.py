"""Make Seeed's COCO Swift-YOLO 320 int8 model runnable in standard TFLite/TFLM: the last three CONCATENATION ops mix
int8 inputs with different scales (class probabilities at 100/256 vs boxes at 2.5), which those runtimes reject.
The probabilities come out of a MUL, which can requantize to any scale, so this rewrites that tensor's scale and
zero point to the concat output's. Usage: patch_coco.py in.tflite out.tflite"""
import sys

import numpy as np
import tflite

src, dst = sys.argv[1], sys.argv[2]
buf = bytearray(open(src, "rb").read())
m = tflite.Model.GetRootAsModel(buf, 0)
g = m.Subgraphs(0)
OPS = {v: k for k, v in tflite.BuiltinOperator.__dict__.items() if not k.startswith("_")}
producer = {}
for n in range(g.OperatorsLength()):
    op = g.Operators(n)
    for k in range(op.OutputsLength()):
        code = m.OperatorCodes(op.OpcodeIndex())
        producer[op.Outputs(k)] = OPS[max(code.BuiltinCode(), code.DeprecatedBuiltinCode())]


def vec_offset(table, field_slot):
    o = table._tab.Offset(field_slot)
    return table._tab.Vector(o) if o else None


patched = 0
for n in range(g.OperatorsLength()):
    op = g.Operators(n)
    code = m.OperatorCodes(op.OpcodeIndex())
    if OPS[max(code.BuiltinCode(), code.DeprecatedBuiltinCode())] != "CONCATENATION":
        continue
    out_q = g.Tensors(op.Outputs(0)).Quantization()
    out_scale, out_zp = float(out_q.ScaleAsNumpy()[0]), int(out_q.ZeroPointAsNumpy()[0])
    for k in range(op.InputsLength()):
        ti = op.Inputs(k)
        q = g.Tensors(ti).Quantization()
        if abs(float(q.ScaleAsNumpy()[0]) - out_scale) < 1e-9:
            continue
        print(f"op {n}: input tensor {ti} from {producer.get(ti)} scale {q.ScaleAsNumpy()[0]:.4f} -> {out_scale:.4f}")
        assert producer.get(ti) == "MUL", "only a MUL output can be requantized safely"
        s_off = vec_offset(q, 8)     # QuantizationParameters vtable slots: min=4, max=6, scale=8, zero_point=10
        z_off = vec_offset(q, 10)
        buf[s_off:s_off + 4] = np.float32(out_scale).tobytes()
        buf[z_off:z_off + 8] = np.int64(out_zp).tobytes()
        patched += 1
open(dst, "wb").write(buf)
print("patched", patched)
