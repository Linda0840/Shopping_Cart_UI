console.log("JavaScript file is loaded.");

function setDatabase() {
    $.post('/set_database', $('#dbForm').serialize(), function(data) {
        $('#message').text(data.message); 
    }).fail(function() {
        $('#message').text("Error: Failed to set the database.");  
    });
}

function loadData() {
    var dbType = $('#dbType').val(); 
    var dbConfig = dbType === 'mongodb' ? 
                   { uri: "mongodb://localhost:27017/", db_name: "ecommerce_db" } :
                   { region: 'us-east-2' }; 
    $.ajax({
        url: '/load-data',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({db_type: dbType, db_config: dbConfig}),
        success: function(response) {
            $('#messages').empty(); 
            if (response.success) {
                alert('Data loaded successfully');
                response.messages.forEach(msg => {
                    $('#messages').append(`<p>${msg}</p>`);
                });
            } else {
                alert('Failed to load data: ' + response.message);
            }
        },
        error: function(xhr, status, error) {
            alert('Error calling the API: ' + error);
        }
    });
}

function login() {
    $.post('/login', $('#loginForm').serialize(), function(data) {
        alert(data.message);
        if (data.status === 'success') {
            $('#authForms').hide();
            if (data.role === 'seller') {
                $('#sellerDashboard').show();
            } else if (data.role === 'buyer') {
                $('#buyerDashboard').show(); 
            }
        }
    }).fail(function() {
        alert("Login failed. Please try again.");
    });
}

function signup() {
    $.post('/signup', $('#signupForm').serialize(), function(data) {
        alert(data.message);
        if (data.status === 'success') {
            $('#authForms').hide(); 
            if (data.role === 'seller') {
                $('#sellerDashboard').show(); 
            } else if (data.role === 'buyer') {
                $('#buyerDashboard').show(); 
            }
        }
    }).fail(function() {
        alert("Signup failed. Please try again.");
    });
}

function viewMyInfo() {
    $.get('/user-info', function(data) {
        if (data.status === 'success') {
            const user = data.user;
            let output = '<h3>User Information:</h3>';
            output += `
                <p id="SelleruserId"><span>Customer ID: </span>${user.customer_id}</p>
                <p id="SelleruserFirstName"><span>First Name:</span> ${user.fname}</p>
                <p id="SelleruserLastName"><span>Last Name:</span> ${user.lname}</p>
                <p id="SelleruserEmail"><span>Email:</span> ${user.email}</p>
                <p id="SelleruserAddress"><span>Address:</span> ${user.address}</p>
                <p id="SelleruserPhone"><span>Phone Number:</span> ${user.phone_number}</p>
                <p id="SelleruserRole"><span>Role:</span> ${user.role}</p>
                <button onclick="toggleEditUserInfoForm()">Edit My Info</button>
            `;
            $('#userInfoOutput').html(output);
            addBackToSellerMenuButton('#userInfoOutput');
        } else {
            alert(data.message);
            $('#userInfoOutput').html(`<p class="error-message">${data.message}</p>`);
            addBackToSellerMenuButton('#userInfoOutput');
        }
    }).fail(function() {
        alert("Failed to fetch user information.");
        $('#userInfoOutput').html('<p class="error-message">Error fetching user information. Please try again later.</p>');
        addBackToSellerMenuButton('#userInfoOutput');
    });
}


function toggleEditUserInfoForm() {
    if ($('#editUserInfoForm').is(':visible')) {
        $('#editUserInfoForm').hide();
    } else {
        $('#editFirstName').val($('#SelleruserFirstName').text().split(': ')[1]);
        $('#editLastName').val($('#SelleruserLastName').text().split(': ')[1]);
        $('#editEmail').val($('#SelleruserEmail').text().split(': ')[1]);
        $('#editAddress').val($('#SelleruserAddress').text().split(': ')[1]);
        $('#editPhoneNumber').val($('#SelleruserPhone').text().split(': ')[1]);
        $('#editUserInfoForm').show();
    }
}

function submitUserInfoUpdate() {
    const updatedData = {
        fname: $('#editFirstName').val() || null,
        lname: $('#editLastName').val() || null,
        email: $('#editEmail').val() || null,
        address: $('#editAddress').val() || null,
        phone_number: $('#editPhoneNumber').val() || null
    };

    $.ajax({
        type: "POST",
        url: "/update-user-info",
        contentType: "application/json",
        data: JSON.stringify(updatedData),
        success: function(response) {
            if(response.status === 'success') {
                alert('User information updated successfully!');
                $('#editUserInfoForm').hide();
            } else {
                alert(response.message);
            }
        },
        error: function(response) {
            alert('Failed to update user information: ' + response.responseText);
        }
    });
}



function logout() {
    $.get('/logout', function(data) {
        alert(data.message);
        if (data.status === 'success') {
            $('#sellerDashboard').hide();
            $('#buyerDashboard').hide();
            $('#viewMyInfo').hide();
            $('#authForms').show();
        }
    }).fail(function() {
        alert("Failed to log out.");
    });
}

/////////////Seller Functionalities///////////////////////////////////////////////////////////////////////

function displayAllProducts() {
    $.ajax({
        url: '/get-products',
        method: 'GET',
        success: function(response) {
            if (response.status === 'success' && response.products.length > 0) {
                const products = response.products;
                let output = '<h2>Product List</h2><div class="product-list">';
                products.forEach(product => {
                    output += `<div class="product">
                                <p>Product ID: <strong>${product.product_id || 'N/A'}</strong></p>
                                <p>Name: <strong>${product.name || 'N/A'}</strong></p>
                                <p>Price: ${product.price || 'N/A'}</p>
                                <p>Stock: ${product.stock || 'N/A'}</p>
                                <p>Rating: ${product.rating || 'N/A'}</p>
                                <p>Description: ${product.description || 'N/A'}</p>
                                <hr></div>`;
                });
                output += '</div>';
                $('#productsOutput').html(output);
                addBackToSellerMenuButton('#productsOutput'); 
            } else {
                $('#productsOutput').html('<p>No products found.</p>');
                addBackToSellerMenuButton('#productsOutput'); 
            }
        },        
        error: function() {
            $('#productsOutput').html('<p>Error fetching products. Please try again later.</p>');
        }
    });
}

function toggleAddProductForm() {
    $('#addProductForm').toggle();  
}

function addProduct() {
    const productData = {
        name: document.getElementById('productName').value,
        price: document.getElementById('productPrice').value,
        stock: document.getElementById('productStock').value,
        description: document.getElementById('productDescription').value
    };

    $.ajax({
        type: "POST",
        url: "/add-product",
        contentType: "application/json",
        data: JSON.stringify(productData),
        success: function(response) {
            alert('Product added successfully!');
            $('#productForm')[0].reset();
            $('#addProductForm').hide();
            addBackToSellerMenuButton('#addProductForm');
        },
        error: function(response) {
            alert('Failed to add product: ' + response.responseText);
        }
    });
}

function toggleDeleteProductForm() {
    $('#deleteProductForm').toggle(); 
}

function deleteProduct() {
    const productId = document.getElementById('productID').value
    if (!productId) {
        alert("Product ID is required.");
    }

    $.ajax({
        type: "POST",
        url: "/delete-product",
        contentType: "application/json",
        data: JSON.stringify({ product_id: productId }),
        success: function(response) {
            alert('Product deleted successfully!');
            $('#deleteForm')[0].reset();  // reset the form
            $('#deleteProductForm').hide();  // hide it
            addBackToSellerMenuButton('#deleteProductForm');
        },
        error: function(response) {
            alert('Failed to delete product: ' + response.responseJSON.message);
        }
    });
}

function toggleUpdateProductForm() {
    $('#updateProductForm').toggle();  
}

function fetchProductInfo() {
    const productId = document.getElementById('updateProductId').value
    if (!productId) {
        alert("Product ID is required.");
    }

    $.ajax({
        type: 'GET',
        url: `/get-product-info/${productId}`,
        success: function(data) {
            if (data.status === 'success') {
                const product = data.product;
                $('#updateProductName').val(product.name).prop('disabled', false);
                $('#updateProductPrice').val(product.price).prop('disabled', false);
                $('#updateProductStock').val(product.stock).prop('disabled', false);
                $('#updateProductDescription').val(product.description).prop('disabled', false);
            } else {
                alert(data.message);
            }
            addBackToSellerMenuButton('#updateProductForm'); 
        },
        error: function() {
            alert('Product not found or error fetching product details.');
        }
    });
}

function submitProductUpdate() {
    const productUpdateData = {
        product_id: document.getElementById('updateProductId').value,
        name: document.getElementById('updateProductName').value,
        price: document.getElementById('updateProductPrice').value,
        stock: document.getElementById('updateProductStock').value,
        description: document.getElementById('updateProductDescription').value
    };

    $.ajax({
        type: "POST",
        url: "/update-product",
        contentType: "application/json",
        data: JSON.stringify(productUpdateData),
        success: function(response) {
            alert('Product updated successfully!');
            $('#updateForm').find('input[type=text], input[type=number]').prop('disabled', true);
        },
        error: function(response) {
            alert('Failed to update product: ' + response.responseJSON.message);
        }
    });
}

function addBackToSellerMenuButton(outputContainer) {
    var backButton = $('<button>Back to Main Menu</button>');
    backButton.on('click', function() {
        $(outputContainer).empty(); 
        $('#sellerDashboard').show(); 
    });
    $(outputContainer).append(backButton);
}

////////////////////////////////////////////////////////////////////////////////////

function addBackToBuyerMenuButton(outputContainer) {
    var backButton = $('<button>Back to Main Menu</button>');
    backButton.on('click', function() {
        $(outputContainer).empty(); // Clear the output container
        $('#buyerDashboard').show(); // Show the buyerDashboard
        $('.search-input-container').hide();
        $('#cancelOrderForm').hide();
    });
    $(outputContainer).append(backButton);
}

function toggleSearchProductWidgets() {
    $('.search-input-container').show();
    $('#searchWidget').toggle();
}

function performProductSearch() {
    const productName = $('#searchInput').val();
    if (!productName) {
        alert("Please enter a product name to search.");
        return;
    }

    $.ajax({
        url: '/search-products',
        method: 'GET',
        data: { name: productName },
        success: function(response) {
            if (response.status === 'success' && response.products.length > 0) {
                const products = response.products;
                let output = '<h3>Search Results</h3><div class="product-list">';
                products.forEach(product => {
                    let quantityInput = `<input type="number" id="qty_${product.product_id}" value="1" min="1" placeholder="Qty">`;
                    let addButton = `<button id="addBtn_${product.product_id}">Add to Cart</button>`;
                    
                    output += `<div class="product">
                                <p>Product ID: ${product.product_id || 'N/A'}</p>
                                <p>Name: ${product.name || 'N/A'}</p>
                                <p>Price: ${product.price || 'N/A'}</p>
                                <p>Stock: ${product.stock || 'N/A'}</p>
                                <p>Description: ${product.description || 'N/A'}</p>
                                ${quantityInput}
                                ${addButton}
                                <hr></div>`;
                });
                output += '</div>';
                $('#searchOutput').html(output);
                products.forEach(product => {
                    $(`#addBtn_${product.product_id}`).on('click', createAddToCartHandler(product, `#qty_${product.product_id}`));
                });
                
                addBackToBuyerMenuButton('#searchOutput');
            } else {
                alert('No products found.');
                addBackToBuyerMenuButton('#searchOutput');
            }
        },
        error: function() {
            alert('Error fetching products. Please try again later.');
        }
    });
}


function createAddToCartHandler(product, quantityInput) {
    return function() {
        // Validate quantity
        var quantity = parseInt($(quantityInput).val());
        if (isNaN(quantity) || quantity <= 0) {
            $('#searchOutput').html("<p>Quantity cannot be negative or zero. Please enter a valid quantity.</p>");
            return;
        }

        // Prepare cart item
        var cartItem = {
            'product_id': product.product_id,
            'name': product.name,
            'quantity': quantity,
            'price': product.price,
            'description': product.description
        };
        console.log(JSON.stringify(cartItem));

        // Send AJAX request to add to cart
        $.ajax({
            url: '/add_to_cart',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(cartItem),
            success: function(response) {
                // Display success message
                alert("Added " + quantity + " unit(s) of " + product.name + " to the cart");
            },
            error: function(error) {
                // Display error message
                console.error('Error:', error);
                alert('Failed to add to cart. Please try again.');
            }
        });
    };
}

function displayCart() {
    $.ajax({
        url: '/display_cart',
        method: 'GET',
        success: function(response) {
            $('#cart-container').empty(); // Clear the container before appending new content

            // Add a header "My Cart" to the top of the cart container
            $('#cart-container').append('<h3>My Cart</h3>');

            if (response.message) {
                // Display the message if provided (e.g., "Cart is empty")
                $('#cart-container').append(`<p>${response.message}</p>`);
            } else {
                // Create a container for the cart items
                let cartContent = $('<div class="cart-items"></div>');
                
                // Iterate through cart items and display each one
                response.cart_items.forEach(function(item) {
                    cartContent.append(
                        `<div class="cart-item">
                            <p><strong>${item.name}</strong> (ID: ${item.product_id})</p>
                            <p>Quantity: ${item.quantity}</p>
                            <p>Price per unit: $${item.price_per_unit}</p>
                            <p>Description: ${item.description}</p>
                        </div>`
                    );
                });

                // Append the cart items container to the main cart container
                $('#cart-container').append(cartContent);

                // Display the total price at the end
                $('#cart-container').append(`<p><strong>Total Price:</strong> $${response.total_price.toFixed(2)}</p>`);

                // Append a button to place the order
                var innerButton = $('<button class="place-order-btn">Place Order</button>');
                innerButton.click(function() {
                    placeOrder(); // Trigger placeOrder function when clicked
                });
                $('#cart-container').append(innerButton);
            }
            addBackToBuyerMenuButton('#cart-container'); // Add a back button for better navigation
        },
        error: function(xhr) {
            console.error('Error:', xhr.responseText);
            alert('Error fetching cart details. Please try again later.');
            addBackToBuyerMenuButton('#cart-container');
        }
    });
}


function placeOrder() {
    $.ajax({
        url: '/place_order',
        method: 'POST',
        contentType: 'application/json',
        success: function(response) {
            $('#cart-container').append(`<p>${response.message}</p>`);
            if (response.messages) {
                response.messages.forEach(function(message) {
                    $('#cart-container').append(`<p>${message}</p>`);
                });
            }
        },
        error: function(xhr, status, error) {
            console.error(xhr.responseText);
            alert('An error occurred while placing your order. Please try again.');
        }
    });
}


function displayOrders() {
    $.ajax({
        url: '/view_my_order',
        method: 'GET',
        success: function(response) {
            $('#orders-container').empty();
            if (response.status === 'success') {
                response.messages.forEach(function(message) {
                    let orderBlock = $('<div class="order-details"></div>');
                    message.order_info.forEach(function(info) {
                        orderBlock.append(`<h4>${info}</h4>`);
                    });
                    message.items_info.forEach(function(item) {
                        orderBlock.append(`<p class="product-item">${item}</p>`);
                    });
                    $('#orders-container').append(orderBlock);
                });
            } else {
                alert(response.message);
            }
            addBackToBuyerMenuButton('#orders-container');
        },
        error: function(xhr, status, error) {
            console.error(xhr.responseText);
            alert('Error fetching orders. Please try again later.');
            addBackToBuyerMenuButton('#orders-container');
        }
    });
}


function toggleCancelOrderForm() {

    $('#cancelOrderForm').toggle();
}

function cancelOrder() {
    var orderId = $('#cancelOrderInput').val().trim();
    if (!orderId) {
        alert("Please enter an order ID to cancel.");
        return;
    }
    
    $.ajax({
        url: '/cancel_order',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ order_id: orderId }),
        success: function(response) {
            if (response.status === 'success') {
                // Join all messages into a single alert if there are multiple messages.
                var messages = response.messages.join("\n");
                alert(messages);
            } else {
                alert(response.message || "An error occurred please try again.");
            }
            addBackToBuyerMenuButton('#cancel-order-container');
        },
        error: function(xhr, status, error) {
            console.error('Error:', xhr.responseText);
            alert("Failed to cancel order: " + xhr.responseText);
            addBackToBuyerMenuButton('#cancel-order-container');
        }
    });
}

function viewBuyerInfo() {
    $.get('/user-info', function(data) {
        if (data.status === 'success') {
            const user = data.user;
            let output = '<h2>User Information:</h2>';
            output += `
                <p id="BuyeruserId"><span>Customer ID: </span>${user.customer_id}</p >
                <p id="BuyeruserFirstName"><span>First Name: </span>${user.fname}</p >
                <p id="BuyeruserLastName"><span>Last Name: </span>${user.lname}</p >
                <p id="BuyeruserEmail"><span>Email: </span>${user.email}</p >
                <p id="BuyeruserAddress"><span>Address: </span>${user.address}</p >
                <p id="BuyeruserPhone"><span>Phone Number: </span>${user.phone_number}</p >
                <p id="BuyeruserRole"><span>Role: </span>${user.role}</p >
                <button onclick="toggleEditBuyerUserInfoForm()">Edit My Info</button>
            `;
            $('#buyerInfoOutput').html(output);
            addBackToBuyerMenuButton('#buyerInfoOutput');
        } else {
            alert(data.message);
            $('#buyerInfoOutput').html('<p>' + data.message + '</p >');
            addBackToBuyerMenuButton('#buyerInfoOutput');
        }
    }).fail(function() {
        alert("Failed to fetch user information.");
        $('#buyerInfoOutput').html('<p>Error fetching user information. Please try again later.</p >');
    });
}

function toggleEditBuyerUserInfoForm() {
    if ($('#editBuyerUserInfoForm').is(':visible')) {
        $('#editBuyerUserInfoForm').hide();
    } else {
        $('#editBuyerFirstName').val($('#BuyeruserFirstName').text().split(': ')[1].trim());
        $('#editBuyerLastName').val($('#BuyeruserLastName').text().split(': ')[1].trim());
        $('#editBuyerEmail').val($('#BuyeruserEmail').text().split(': ')[1].trim());
        $('#editBuyerAddress').val($('#BuyeruserAddress').text().split(': ')[1].trim());
        $('#editBuyerPhoneNumber').val($('#BuyeruserPhone').text().split(': ')[1].trim());
        $('#editBuyerUserInfoForm').show();
    }
}


function submitBuyerUserInfoUpdate() {
    const updatedData = {
        fname: $('#editBuyerFirstName').val(),
        lname: $('#editBuyerLastName').val(),
        email: $('#editBuyerEmail').val(),
        address: $('#editBuyerAddress').val(),
        phone_number: $('#editBuyerPhoneNumber').val()
    };

    $.ajax({
        type: "POST",
        url: "/update-user-info", 
        contentType: "application/json",
        data: JSON.stringify(updatedData),
        success: function(response) {
            if(response.status === 'success') {
                alert('User information updated successfully!');
                $('#editBuyerUserInfoForm').hide();
            } else {
                alert(response.message);
            }
        },
        error: function(response) {
            alert('Failed to update user information: ' + response.responseText);
        }
    });
}
