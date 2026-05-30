<?php
/*
 * @Author: Fox Blue
 * @Date: 2021-06-28
 * @Description: Vulnerability Verification - CALCULATOR ONLY, no destructive actions
 */

$result = '';
$num1 = isset($_POST['num1']) ? floatval($_POST['num1']) : null;
$num2 = isset($_POST['num2']) ? floatval($_POST['num2']) : null;
$op   = isset($_POST['op'])   ? $_POST['op'] : '';

if ($num1 !== null && $num2 !== null && $op) {
    switch ($op) {
        case '+': $result = $num1 + $num2; break;
        case '-': $result = $num1 - $num2; break;
        case '*': $result = $num1 * $num2; break;
        case '/': $result = ($num2 != 0) ? $num1 / $num2 : 'Error: division by zero'; break;
        default:  $result = 'Error: unknown operator';
    }
}
?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="fox-calc-verify" content="1">
<title>Vulnerability Verification</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:Arial,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;background:linear-gradient(135deg,#667eea,#764ba2)}
.card{background:#fff;padding:40px;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.3);text-align:center;max-width:400px;width:90%}
h2{color:#333;margin-bottom:8px;font-size:22px}
.sub{color:#999;font-size:13px;margin-bottom:24px}
.row{display:flex;gap:8px;margin-bottom:12px;justify-content:center}
.row input,.row select{padding:10px 14px;border:2px solid #e0e0e0;border-radius:8px;font-size:15px;outline:none;transition:border .2s}
.row input:focus,.row select:focus{border-color:#667eea}
.row input{width:100px}
.row select{width:52px}
.btn{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;padding:12px 40px;border-radius:8px;font-size:16px;cursor:pointer;transition:opacity .2s}
.btn:hover{opacity:.9}
.result{font-size:28px;font-weight:700;color:#667eea;margin-top:20px;padding:12px;background:#f5f3ff;border-radius:8px;word-break:break-all}
.footer{margin-top:24px;font-size:11px;color:#bbb}
.tag{color:#e74c3c;font-weight:700}
</style>
</head>
<body>
<div class="card">
    <h2>🔬 Vulnerability Verification</h2>
    <p class="sub">Remote File Write — Calculator PoC (harmless)</p>
    <form method="post">
        <div class="row">
            <input type="text" name="num1" placeholder="Number" required>
            <select name="op">
                <option value="+">+</option>
                <option value="-">−</option>
                <option value="*">×</option>
                <option value="/">÷</option>
            </select>
            <input type="text" name="num2" placeholder="Number" required>
        </div>
        <button class="btn" type="submit">Calculate</button>
    </form>
    <div class="result"><?= $result !== '' ? htmlspecialchars((string)$result) : 'Awaiting input' ?></div>
    <div class="footer">
        <span class="tag">⚠ VULNERABLE</span> — Server allows remote file write via <code>get_usercode</code>
    </div>
</div>
</body>
</html>
