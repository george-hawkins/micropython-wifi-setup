Example requests
================

Set the address to use for all requests:

    $ ADDR=192.168.0.178

Request the root document:

    $ curl -v $ADDR

Or:

    $ curl -v $ADDR/index.html

Deliberately generate a 404 (Not Found):

    $ curl -v $ADDR/unknown

Set things up to make including the JSON accept header easier and make the same request with this header:

    $ JSON='Accept: application/json'
    $ curl -v -H "$JSON" $ADDR/unknown

The response body now comes back as JSON rather than HTML.

Some requests only return JSON:

    $ curl -v $ADDR/access-points

There's a slight pause for this request as it goes off and scans for access points.

If you've got `jq` installed try it again like so:

    $ curl -s -v $ADDR/access-points | jq .

Try the authentication endpoint:

    $ curl -v -H "$JSON" --data 'bssid=alpha&password=beta' $ADDR/authenticate

Get it to fail by not providing a password:

    $ curl -v -H "$JSON" --data 'bssid=alpha' $ADDR/authenticate

Oddy `-v` doesn't show the data sent with `--data`, if you want to see what exactly is sent you need to use `--trace-ascii`:

    $ curl --trace-ascii - -H "$JSON" --data 'bssid=alpha&password=beta' $ADDR/authenticate

The output isn't very readable - but everything is there.

Finally you can try a more unusual HTTP [method](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods):

    $ curl -v -X OPTIONS $ADDR/unknown

Perhaps a little oddly, the default handler for `OPTIONS` doesn't care if the given path exists or not.

Unless you've reconfigured the `OptionsModule` there's no interesting additional headers in the `OPTIONS` response.
