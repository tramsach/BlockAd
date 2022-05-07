# Tự tạo chứng chỉ CA cho Surge, Quantumult #

### Chuẩn bị ###
- OpenSSL
- Surge hoặc Quantumult

### Bắt đầu ###

1. Tạo thư mục
```
mkdir tên-thư-mục
```
2. Tiếp đó
```
cd tên-thư-mục
```
3. Tạo khóa CA
```
openssl genrsa -out ca.key 2048
```
4. Tạo chứng chỉ CA
````
openssl req -x509 -new -nodes -key ca.key -subj "/C=VN/ST=Hanoi/L=Hanoi/O=TRAMSACH/OU=TRAMSACH/CN=TRAMSACH/emailAddress=son@tramsach.com" -days 36500 -out ca.crt
````
trong đó:
- **C** là Vùng, khu vực: VN
- **ST** thành phố, thị trấn
- **L** là vị trí location
- **O** là tên tổ chức
- **OU** là tên đơn vị, tổ chức
- **CN** là tên thường dùng
- **emailAddress** là địa chỉ email của bạn
- **day** là số ngày của chứng chỉ.

5. Chuyển đổi định dạng CA sang p12 và đặt mật khẩu 

```
openssl pkcs12 -export -clcerts -in ./ca.crt -inkey ca.key -out ca.p12 -password pass:tramsach
```
6. Mã hóa base64 cho chứng chỉ p12
```
base64 ca.p12
```
7. Base64一行不能超过76字符，超过则添加回车换行符。如果因为换行的原因，不能安装证书，可以使用 -w 参数
```
base64 -w 0 ca.p12
```

8. Mở ứng dụng copy mật khẩu và key ở dạng base64 vào, rồi cài đặt nó.