# Examples

## sample-project

展示正式完整脚本合同、模板页处理、证据映射、锁定上屏文字、页级合同注释、视觉合同和演讲者备注。

```bash
python scripts/validate_script.py examples/sample-project/10-script-final.md --strict
python scripts/validate_project.py examples/sample-project --strict
```

## golden

保存实际下游派生产物，用于回归验证单页ImageGen送图契约。

```bash
python scripts/validate_imagegen_contract.py \
  examples/golden/06953cb7-5f43-4d00-8b23-72af9dd467bc.md
```
